import math
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.database import engine
from app.domain.chat import ChatMessage
from app.providers.base import ChatProvider
from app.repositories.conversation_repository import ConversationRepository
from app.services.conversation_chat_service import ConversationChatService


class RecordingProvider(ChatProvider):
    def __init__(self) -> None:
        self.calls: list[list[ChatMessage]] = []
        self.response_number = 0

    @property
    def name(self) -> str:
        return "test"

    @property
    def model(self) -> str:
        return "test-model"

    @property
    def context_window(self) -> int:
        return 4_096

    def count_tokens(
        self,
        messages: Sequence[ChatMessage],
    ) -> int:
        return math.ceil(
            sum(len(message.role) + len(message.content) for message in messages)
            / 3
        )

    def generate(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
    ) -> str:
        del max_output_tokens
        captured_messages = list(messages)
        self.calls.append(captured_messages)

        if "Update the conversation memory" in captured_messages[0].content:
            return (
                "# Conversation Memory\n\n"
                "## Objective\nMaintain pump reliability.\n\n"
                "## Equipment\n- Pump P-101\n\n"
                "## Known Facts\n\n## Assumptions\n\n## Decisions\n\n"
                "## Recommended Actions\n\n## Open Questions"
            )

        self.response_number += 1
        return f"Assistant response {self.response_number}"


def test_conversation_service_persists_follow_up_context_and_memory() -> None:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        provider = RecordingProvider()
        conversation = ConversationRepository(session).create("Pump session")
        service = ConversationChatService(session, provider)

        first_user, first_assistant, first_memory_status = service.respond(
            conversation.id,
            "How do I troubleshoot pump P-101?",
        )
        second_user, second_assistant, second_memory_status = service.respond(
            conversation.id,
            "What about the bearings?",
        )

        reloaded = ConversationRepository(session).get_by_id(conversation.id)
        second_response_context = provider.calls[2]
        second_context_contents = [
            message.content for message in second_response_context
        ]

        assert first_user.sequence_number == 1
        assert first_assistant.sequence_number == 2
        assert second_user.sequence_number == 3
        assert second_assistant.sequence_number == 4
        assert first_memory_status == "completed"
        assert second_memory_status == "completed"
        assert "How do I troubleshoot pump P-101?" in second_context_contents
        assert "Assistant response 1" in second_context_contents
        assert second_context_contents[-1] == "What about the bearings?"
        assert reloaded is not None
        assert reloaded.message_count == 4
        assert reloaded.memory_through_sequence_number == 4
        assert reloaded.memory_update_status == "completed"
        assert len(reloaded.messages) == 4
        assert len(reloaded.memory_revisions) == 2
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_conversation_service_sets_summary_title_from_first_message() -> None:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        provider = RecordingProvider()
        conversation = ConversationRepository(session).create()
        service = ConversationChatService(session, provider)

        service.respond(
            conversation.id,
            "Can you help me troubleshoot repeated failures on pump P-101?",
        )

        reloaded = ConversationRepository(session).get_by_id(conversation.id)

        assert reloaded is not None
        assert reloaded.title == "Troubleshoot Repeated Failures Pump P-101"
    finally:
        session.close()
        transaction.rollback()
        connection.close()
