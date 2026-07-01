import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.database import get_database_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.feedback_response import FeedbackResponse


class FakeFeedbackSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commit_count = 0
        self.refreshed: list[Any] = []

    def add(self, item: Any) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, item: Any) -> None:
        if item.id is None:
            item.id = uuid.uuid4()
        if item.created_at is None:
            item.created_at = datetime.now(UTC)
        self.refreshed.append(item)


def test_feedback_submission_persists_signed_in_user_response() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    session = FakeFeedbackSession()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_database_session] = lambda: session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/feedback",
                json={
                    "usefulness_rating": 5,
                    "confidence_rating": 4,
                    "most_useful": "repeat_failures",
                    "improvement_priority": "upload_import_workflow",
                    "future_feature_interest": ["upload_data"],
                    "comment": "Useful prioritization signal.",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_database_session, None)

    assert response.status_code == 201
    assert session.commit_count == 1
    assert len(session.added) == 1
    feedback = session.added[0]
    assert isinstance(feedback, FeedbackResponse)
    assert feedback.user_id == user.id
    assert feedback.usefulness_rating == 5
    assert feedback.confidence_rating == 4
    assert feedback.most_useful == "repeat_failures"
    assert feedback.improvement_priority == "upload_import_workflow"
    assert feedback.future_feature_interest == ["upload_data"]
    assert feedback.comment == "Useful prioritization signal."
