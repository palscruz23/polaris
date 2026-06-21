import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.domain.chat import ChatMessage
from app.exceptions import (
    ChatServiceError,
    ConversationBusyError,
    ConversationNotFoundError,
    MemoryCompactionRequired,
)
from app.models.message import Message
from app.prompts.reliability_agent import RELIABILITY_AGENT_SYSTEM_PROMPT
from app.providers.base import ChatProvider
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.context_builder import ContextBuilder
from app.services.memory_service import MemoryService


class ConversationChatService:
    def __init__(
        self,
        session: Session,
        provider: ChatProvider,
    ):
        self.session = session
        self.provider = provider
        self.conversations = ConversationRepository(session)
        self.messages = MessageRepository(session)
        self.context_builder = ContextBuilder(provider)
        self.memory_service = MemoryService(provider)

    def respond(
        self,
        conversation_id: uuid.UUID,
        content: str,
    ) -> tuple[Message, Message, str]:
        conversation = self.conversations.get_for_update(conversation_id)

        if conversation is None:
            raise ConversationNotFoundError

        processing_is_stale = (
            conversation.processing_started_at is not None
            and datetime.now(UTC) - conversation.processing_started_at
            > timedelta(minutes=2)
        )

        if conversation.is_processing and not processing_is_stale:
            self.session.rollback()
            raise ConversationBusyError

        self.conversations.begin_processing(conversation)

        user_message = self.messages.create(
            conversation=conversation,
            role="user",
            content=content,
        )

        history_records = self.messages.list_for_conversation(
            conversation.id,
            through_sequence_number=user_message.sequence_number - 1,
        )
        history = self.messages.to_chat_messages(history_records)

        try:
            try:
                context = self.context_builder.build(
                    system_prompt=RELIABILITY_AGENT_SYSTEM_PROMPT,
                    memory_markdown=conversation.memory_markdown,
                    history=history,
                    current_user_message=content,
                )
            except MemoryCompactionRequired:
                compacted_memory = self.memory_service.compact(
                    conversation.memory_markdown
                )
                locked_conversation = self.conversations.get_for_update(
                    conversation_id
                )

                if locked_conversation is None:
                    raise ConversationNotFoundError

                self.conversations.save_memory(
                    conversation=locked_conversation,
                    memory_markdown=compacted_memory,
                    through_sequence_number=(
                        locked_conversation.memory_through_sequence_number
                    ),
                )
                context = self.context_builder.build(
                    system_prompt=RELIABILITY_AGENT_SYSTEM_PROMPT,
                    memory_markdown=compacted_memory,
                    history=history,
                    current_user_message=content,
                )

            assistant_content = self.provider.generate(
                messages=context.messages,
                max_output_tokens=context.max_output_tokens,
            )
        except Exception:
            self._clear_processing(conversation_id)
            raise

        locked_conversation = self.conversations.get_for_update(conversation_id)

        if locked_conversation is None:
            raise ConversationNotFoundError

        assistant_message = self.messages.create(
            conversation=locked_conversation,
            role="assistant",
            content=assistant_content,
            provider=self.provider.name,
            model=self.provider.model,
        )
        self._clear_processing(conversation_id)

        memory_status = self._update_memory(
            conversation_id=conversation_id,
            previous_memory=locked_conversation.memory_markdown,
            user_message=content,
            assistant_message=assistant_content,
            through_sequence_number=assistant_message.sequence_number,
        )

        return user_message, assistant_message, memory_status

    def _clear_processing(
        self,
        conversation_id: uuid.UUID,
    ) -> None:
        conversation = self.conversations.get_for_update(conversation_id)

        if conversation is not None:
            self.conversations.end_processing(conversation)

    def _update_memory(
        self,
        conversation_id: uuid.UUID,
        previous_memory: str,
        user_message: str,
        assistant_message: str,
        through_sequence_number: int,
    ) -> str:
        conversation = self.conversations.get_for_update(conversation_id)

        if conversation is None:
            raise ConversationNotFoundError

        self.conversations.mark_memory_update_pending(conversation)

        try:
            memory_markdown = self.memory_service.update(
                previous_memory=previous_memory,
                user_message=user_message,
                assistant_message=assistant_message,
            )
        except ChatServiceError as error:
            conversation = self.conversations.get_for_update(conversation_id)

            if conversation is not None:
                self.conversations.mark_memory_update_failed(
                    conversation,
                    str(error),
                )

            return "failed"

        conversation = self.conversations.get_for_update(conversation_id)

        if conversation is None:
            raise ConversationNotFoundError

        self.conversations.save_memory(
            conversation=conversation,
            memory_markdown=memory_markdown,
            through_sequence_number=through_sequence_number,
        )

        return "completed"
