import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.domain.progress import report_progress
from app.main import app
from app.routes import conversations


class FakeSessionContext:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, *args: object) -> None:
        del args


class ProgressService:
    def __init__(self, session: object, provider: object):
        del session, provider

    def respond(
        self,
        conversation_id: uuid.UUID,
        content: str,
        progress,
    ):
        report_progress(
            progress,
            stage="reviewing_request",
            message="Reliability Agent is reviewing your request.",
        )
        report_progress(
            progress,
            stage="specialist_started",
            specialist="maintenance_strategy",
            message=(
                "Reliability Agent is coordinating with the Maintenance Strategy Agent."
            ),
        )
        now = datetime.now(UTC)
        user_message = SimpleNamespace(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role="user",
            content=content,
            sequence_number=1,
            provider=None,
            model=None,
            created_at=now,
        )
        assistant_message = SimpleNamespace(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role="assistant",
            content="Maintenance strategy review complete.",
            sequence_number=2,
            provider="test",
            model="test-model",
            created_at=now,
        )

        return user_message, assistant_message, "completed"


def test_stream_message_returns_progress_before_completed_exchange(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        conversations,
        "SessionLocal",
        FakeSessionContext,
    )
    monkeypatch.setattr(
        conversations,
        "ConversationChatService",
        ProgressService,
    )
    selected_models: list[str | None] = []

    def build_provider(model_id: str | None = None) -> object:
        selected_models.append(model_id)
        return object()

    monkeypatch.setattr(
        conversations,
        "get_chat_provider",
        build_provider,
    )
    conversation_id = uuid.uuid4()

    with TestClient(app) as client:
        response = client.post(
            f"/conversations/{conversation_id}/messages/stream",
            json={
                "content": "Review the strategy for P-101.",
                "model": "anthropic/claude-sonnet-4.6",
            },
        )

    events = [
        json.loads(line)
        for line in response.text.splitlines()
        if line
    ]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/x-ndjson"
    )
    assert [event["type"] for event in events] == [
        "progress",
        "progress",
        "complete",
    ]
    assert events[1]["message"] == (
        "Reliability Agent is coordinating with the Maintenance Strategy Agent."
    )
    assert events[-1]["exchange"]["assistant_message"]["content"] == (
        "Maintenance strategy review complete."
    )
    assert selected_models == ["anthropic/claude-sonnet-4.6"]
