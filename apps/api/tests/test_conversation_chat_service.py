import math
import uuid
from collections.abc import Sequence

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database import engine
from app.domain.chat import ChatMessage
from app.domain.orchestration import (
    AgentModelCallTrace,
    AgentOrchestrationResponse,
    AgentToolCall,
    AgentToolExchange,
    AgentToolResult,
)
from app.exceptions import ConversationNotFoundError
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


class MetadataOrchestrator:
    def respond_with_metadata(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        progress=None,
        model_call_observer=None,
    ) -> AgentOrchestrationResponse:
        del messages, max_output_tokens, progress
        if model_call_observer is not None:
            model_call_observer(
                AgentModelCallTrace(
                    call_type="agent_tool_selection",
                    status="completed",
                    latency_ms=42,
                    input_tokens_estimate=120,
                    output_tokens_estimate=20,
                    max_output_tokens=500,
                    requested_tool_count=4,
                    response_tool_call_count=1,
                )
            )
        return AgentOrchestrationResponse(
            content="Review complete.",
            tool_calls=(
                AgentToolExchange(
                    call=AgentToolCall(
                        id="call-1",
                        name="review_maintenance_strategy",
                        arguments={"equipment_numbers": ["P-101"]},
                    ),
                    result=AgentToolResult(
                        call_id="call-1",
                        tool_name="review_maintenance_strategy",
                        content='{"recommendation":"modify"}',
                    ),
                ),
            ),
        )


def _database_session_or_skip() -> tuple[object, object, Session]:
    try:
        connection = engine.connect()
    except OperationalError as error:
        pytest.skip(f"Postgres is unavailable: {error}")

    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )
    return connection, transaction, session


def test_conversation_service_persists_follow_up_context_and_memory() -> None:
    connection, transaction, session = _database_session_or_skip()

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
        second_response_context = next(
            call
            for call in provider.calls
            if call[-1].content == "What about the bearings?"
        )
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
    connection, transaction, session = _database_session_or_skip()

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


def test_conversation_service_rejects_conversation_owned_by_another_user() -> None:
    class RejectingConversationRepository:
        def __init__(self) -> None:
            self.received_user_id: uuid.UUID | None = None

        def get_for_update(
            self,
            conversation_id: uuid.UUID,
            user_id: uuid.UUID | None = None,
        ) -> None:
            del conversation_id
            self.received_user_id = user_id
            return None

    provider = RecordingProvider()
    user_id = uuid.uuid4()
    repository = RejectingConversationRepository()
    service = ConversationChatService(object(), provider)  # type: ignore[arg-type]
    service.conversations = repository  # type: ignore[assignment]

    with pytest.raises(ConversationNotFoundError):
        service.respond(
            uuid.uuid4(),
            "Review P-101 failures.",
            user_id=user_id,
        )

    assert repository.received_user_id == user_id
    assert provider.calls == []


def test_conversation_service_persists_agent_tool_metadata() -> None:
    connection, transaction, session = _database_session_or_skip()

    try:
        provider = RecordingProvider()
        conversation = ConversationRepository(session).create()
        service = ConversationChatService(
            session,
            provider,
            orchestrator=MetadataOrchestrator(),  # type: ignore[arg-type]
        )

        user_message, assistant_message, _ = service.respond(
            conversation.id,
            "Review P-101 strategy.",
        )
        session.refresh(conversation)

        assert assistant_message.metadata_ == {
            "tool_calls": [
                {
                    "sequence": 1,
                    "id": "call-1",
                    "agent": "reliability_agent",
                    "target_agent": "maintenance_strategy",
                    "tool": "review_maintenance_strategy",
                    "arguments": {"equipment_numbers": ["P-101"]},
                    "result": '{"recommendation":"modify"}',
                    "is_error": False,
                    "sub_calls": [],
                }
            ]
        }
        assert len(conversation.agent_runs) == 1
        agent_run = conversation.agent_runs[0]
        assert agent_run.user_message_id == user_message.id
        assert agent_run.assistant_message_id == assistant_message.id
        assert agent_run.status == "completed"
        assert agent_run.provider == "test"
        assert agent_run.model == "test-model"
        assert agent_run.tool_call_count == 1
        assert agent_run.tool_metadata == assistant_message.metadata_
        assert len(agent_run.model_calls) == 1
        assert agent_run.model_calls[0].call_type == "agent_tool_selection"
        assert agent_run.model_calls[0].latency_ms == 42
        assert agent_run.model_calls[0].requested_tool_count == 4
    finally:
        session.close()
        transaction.rollback()
        connection.close()
