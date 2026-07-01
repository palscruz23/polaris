import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from time import perf_counter

from sqlalchemy.orm import Session

from app.agents.registry import SpecialistRegistry
from app.domain.chat import ChatMessage
from app.domain.orchestration import AgentInternalCall, AgentToolExchange
from app.domain.progress import ProgressCallback
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
from app.repositories.observability_repository import ObservabilityRepository
from app.services.context_builder import ContextBuilder
from app.services.memory_service import MemoryService
from app.services.reliability_agent_orchestrator import (
    ReliabilityAgentOrchestrator,
)

TITLE_STOP_WORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "can",
    "could",
    "do",
    "for",
    "from",
    "help",
    "how",
    "i",
    "in",
    "is",
    "me",
    "my",
    "of",
    "on",
    "please",
    "should",
    "the",
    "to",
    "what",
    "with",
    "you",
}


class ConversationChatService:
    def __init__(
        self,
        session: Session,
        provider: ChatProvider,
        orchestrator: ReliabilityAgentOrchestrator | None = None,
    ):
        self.session = session
        self.provider = provider
        self.conversations = ConversationRepository(session)
        self.messages = MessageRepository(session)
        self.observability = ObservabilityRepository(session)
        self.context_builder = ContextBuilder(provider)
        self.memory_service = MemoryService(provider)
        self.orchestrator = orchestrator or ReliabilityAgentOrchestrator(
            provider=provider,
            registry=SpecialistRegistry(session),
        )

    def respond(
        self,
        conversation_id: uuid.UUID,
        content: str,
        user_id: uuid.UUID | None = None,
        progress: ProgressCallback | None = None,
    ) -> tuple[Message, Message, str]:
        conversation = self.conversations.get_for_update(
            conversation_id,
            user_id=user_id,
        )

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

        if conversation.title is None:
            self.conversations.set_title(
                conversation=conversation,
                title=self._title_from_message(content),
            )

        history_records = self.messages.list_for_conversation(
            conversation.id,
            through_sequence_number=user_message.sequence_number - 1,
        )
        history = self.messages.to_chat_messages(history_records)

        agent_run = None
        run_started_at = perf_counter()
        memory_operations: list[dict] = []

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
                    conversation_id,
                    user_id=user_id,
                )

                if locked_conversation is None:
                    raise ConversationNotFoundError from None

                self.conversations.save_memory(
                    conversation=locked_conversation,
                    memory_markdown=compacted_memory,
                    through_sequence_number=(
                        locked_conversation.memory_through_sequence_number
                    ),
                )
                memory_operations.append({
                    "sequence": 0,
                    "call_type": "memory_compaction",
                    "message": "Compact conversation memory to stay within context limit",
                })
                context = self.context_builder.build(
                    system_prompt=RELIABILITY_AGENT_SYSTEM_PROMPT,
                    memory_markdown=compacted_memory,
                    history=history,
                    current_user_message=content,
                )

            agent_run = self.observability.start_agent_run(
                conversation_id=conversation.id,
                user_message_id=user_message.id,
                provider=self.provider.name,
                model=self.provider.model,
                input_tokens_estimate=self.provider.count_tokens(
                    context.messages
                ),
            )
            agent_response = self.orchestrator.respond_with_metadata(
                messages=context.messages,
                max_output_tokens=context.max_output_tokens,
                progress=progress,
                model_call_observer=lambda trace: (
                    self.observability.record_model_call(
                        agent_run=agent_run,
                        trace=trace,
                    )
                ),
            )
            assistant_content = agent_response.content
        except Exception as error:
            if agent_run is not None:
                self.observability.fail_agent_run(
                    agent_run=agent_run,
                    total_latency_ms=self._elapsed_ms(run_started_at),
                    error=error,
                )
            self._clear_processing(conversation_id, user_id=user_id)
            raise

        locked_conversation = self.conversations.get_for_update(
            conversation_id,
            user_id=user_id,
        )

        if locked_conversation is None:
            raise ConversationNotFoundError

        tool_metadata = self._message_metadata(
            tool_calls=agent_response.tool_calls,
            internal_calls=agent_response.internal_calls,
            memory_operations=memory_operations,
        )
        assistant_message = self.messages.create(
            conversation=locked_conversation,
            role="assistant",
            content=assistant_content,
            provider=self.provider.name,
            model=self.provider.model,
            metadata=tool_metadata,
        )
        if agent_run is not None:
            self.observability.complete_agent_run(
                agent_run=agent_run,
                assistant_message_id=assistant_message.id,
                total_latency_ms=self._elapsed_ms(run_started_at),
                output_tokens_estimate=self.provider.count_tokens(
                    [
                        ChatMessage(
                            role="assistant",
                            content=assistant_content,
                        )
                    ]
                ),
                tool_call_count=len(agent_response.tool_calls),
                tool_metadata=tool_metadata,
            )
        self._clear_processing(conversation_id, user_id=user_id)

        memory_status = self._update_memory(
            conversation_id=conversation_id,
            user_id=user_id,
            previous_memory=locked_conversation.memory_markdown,
            user_message=content,
            assistant_message=assistant_content,
            through_sequence_number=assistant_message.sequence_number,
        )

        if memory_status == "completed":
            memory_operations.append({
                "sequence": 0,
                "call_type": "memory_update",
                "message": "Update conversation memory with new information",
            })

        return user_message, assistant_message, memory_status

    @staticmethod
    def _elapsed_ms(start: float) -> int:
        return max(0, round((perf_counter() - start) * 1000))

    @staticmethod
    def _message_metadata(
        tool_calls: Sequence[AgentToolExchange],
        internal_calls: Sequence[AgentInternalCall] = (),
        memory_operations: Sequence[dict] = (),
    ) -> dict | None:
        if not tool_calls and not internal_calls and not memory_operations:
            return None

        metadata: dict = {}

        if internal_calls or memory_operations:
            metadata["internal_calls"] = [
                *[
                    {
                        "sequence": index,
                        "call_type": ic.call_type,
                        "message": ic.message,
                    }
                    for index, ic in enumerate(internal_calls, start=1)
                ],
                *memory_operations,
            ]

        if tool_calls:
            metadata["tool_calls"] = [
                {
                    "sequence": index,
                    "id": exchange.call.id,
                    "agent": "reliability_agent",
                    "target_agent": ReliabilityAgentOrchestrator._specialist_name(
                        exchange.call.name
                    ),
                    "tool": exchange.call.name,
                    "arguments": exchange.call.arguments,
                    "result": exchange.result.content,
                    "is_error": exchange.result.is_error,
                    "sub_calls": [
                        {
                            "agent": sub.specialist,
                            "tool": sub.tool,
                            "message": sub.message,
                        }
                        for sub in exchange.result.sub_calls
                    ],
                }
                for index, exchange in enumerate(tool_calls, start=1)
            ]

        return metadata

    @staticmethod
    def _title_from_message(content: str) -> str:
        cleaned_words = [
            word.strip(".,!?;:()[]{}\"'")
            for word in content.split()
        ]
        words = [word for word in cleaned_words if word]
        summary_words = [
            word
            for word in words
            if word.lower() not in TITLE_STOP_WORDS
        ]

        summary_words = (
            words[:6]
            if len(summary_words) < 3
            else summary_words[:7]
        )

        title = " ".join(
            word if word.isupper() or any(char.isdigit() for char in word)
            else word.capitalize()
            for word in summary_words
        )

        if len(title) <= 60:
            return title or "New Reliability Chat"

        return f"{title[:57].rstrip()}..."

    def _clear_processing(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> None:
        conversation = self.conversations.get_for_update(
            conversation_id,
            user_id=user_id,
        )

        if conversation is not None:
            self.conversations.end_processing(conversation)

    def _update_memory(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID | None,
        previous_memory: str,
        user_message: str,
        assistant_message: str,
        through_sequence_number: int,
    ) -> str:
        conversation = self.conversations.get_for_update(
            conversation_id,
            user_id=user_id,
        )

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
            conversation = self.conversations.get_for_update(
                conversation_id,
                user_id=user_id,
            )

            if conversation is not None:
                self.conversations.mark_memory_update_failed(
                    conversation,
                    str(error),
                )

            return "failed"

        conversation = self.conversations.get_for_update(
            conversation_id,
            user_id=user_id,
        )

        if conversation is None:
            raise ConversationNotFoundError

        self.conversations.save_memory(
            conversation=conversation,
            memory_markdown=memory_markdown,
            through_sequence_number=through_sequence_number,
        )

        return "completed"
