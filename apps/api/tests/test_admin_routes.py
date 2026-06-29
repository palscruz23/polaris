import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database import get_database_session
from app.dependencies.auth import (
    get_current_admin_user,
    get_current_user,
    user_is_admin,
)
from app.main import app
from app.models.user import User


def test_user_is_admin_denies_without_allowlist() -> None:
    user = User(
        email="reliability@example.com",
        auth_provider="google",
        provider_subject="user-1",
    )

    assert user_is_admin(user, ()) is False


def test_user_is_admin_checks_configured_email_allowlist() -> None:
    user = User(
        email="Reliability@Example.com",
        auth_provider="google",
        provider_subject="user-1",
    )

    assert user_is_admin(user, ("reliability@example.com",)) is True
    assert user_is_admin(user, ("other@example.com",)) is False


def test_admin_browser_path_redirects_to_frontend() -> None:
    with TestClient(app) as client:
        response = client.get("/admin", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "http://localhost:3000/admin"


class FakeScalarResult:
    def __init__(self, items: list[object]):
        self.items = items

    def all(self) -> list[object]:
        return self.items


class FakeSession:
    def scalars(self, _statement: object) -> FakeScalarResult:
        smoke_suite = SimpleNamespace(
            id=uuid.uuid4(),
            name="smoke",
        )
        prod_suite = SimpleNamespace(
            id=uuid.uuid4(),
            name="prod",
        )
        eval_case = SimpleNamespace(
            id=uuid.uuid4(),
            name="equipment_master_search",
            prompt="Find pump equipment.",
        )
        result = SimpleNamespace(
            id=uuid.uuid4(),
            eval_case_id=eval_case.id,
            case=eval_case,
            status="passed",
            score=1.0,
            scores={"routing": 1.0},
            checks=[],
            failure_category=None,
            assistant_answer="Pump equipment found.",
            trace={"tool_calls": []},
            error_type=None,
            error_message=None,
            conversation_id=uuid.uuid4(),
            agent_run_id=uuid.uuid4(),
            created_at=datetime.now(UTC),
        )
        smoke_run = SimpleNamespace(
            id=uuid.uuid4(),
            suite_id=smoke_suite.id,
            suite=smoke_suite,
            provider="test",
            model="test-model",
            status="completed",
            case_count=1,
            passed_count=1,
            failed_count=0,
            aggregate_score=1.0,
            git_commit="abc123",
            dataset_version="test",
            run_metadata={"source": "test"},
            error_type=None,
            error_message=None,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            results=[result],
        )
        prod_run = SimpleNamespace(
            id=uuid.uuid4(),
            suite_id=prod_suite.id,
            suite=prod_suite,
            provider="test",
            model="test-model",
            status="completed",
            case_count=1,
            passed_count=0,
            failed_count=1,
            aggregate_score=0.5,
            git_commit="abc123",
            dataset_version="test",
            run_metadata={"source": "test", "run_purpose": "nightly"},
            error_type=None,
            error_message=None,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            results=[],
        )

        return FakeScalarResult([smoke_run, prod_run])

    def execute(self, _statement: object):
        user_id = uuid.uuid4()

        return FakeScalarResult([
            SimpleNamespace(
                user_id=user_id,
                login_count=2,
                latest_login_at=datetime.now(UTC),
            )
        ])


class FakeUsersSession:
    def __init__(self) -> None:
        self.user_id = uuid.uuid4()

    def scalars(self, _statement: object) -> FakeScalarResult:
        return FakeScalarResult([
            SimpleNamespace(
                id=uuid.uuid4(),
                user_id=self.user_id,
                created_at=datetime.now(UTC),
            )
        ])

    def execute(self, _statement: object):
        return FakeScalarResult([
            SimpleNamespace(
                user_id=self.user_id,
                login_count=2,
                latest_login_at=datetime.now(UTC),
            )
        ])


def test_admin_evaluations_endpoint_returns_dashboard() -> None:
    fake_admin = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@example.com",
        display_name="Admin",
        avatar_url=None,
        auth_provider="google",
        created_at=datetime.now(UTC),
    )
    app.dependency_overrides[get_current_user] = lambda: fake_admin
    app.dependency_overrides[get_current_admin_user] = lambda: fake_admin
    app.dependency_overrides[get_database_session] = lambda: FakeSession()

    try:
        with TestClient(app) as client:
            response = client.get("/admin/evaluations")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_admin_user, None)
        app.dependency_overrides.pop(get_database_session, None)

    assert response.status_code == 200
    body = response.json()
    assert body["runs"][0]["suite_name"] == "smoke"
    assert body["runs"][0]["run_metadata"] == {"source": "test"}
    assert [suite["suite_name"] for suite in body["suites"]] == [
        "smoke",
        "prod",
    ]
    assert body["suites"][0]["latest_run"]["suite_name"] == "smoke"
    assert body["suites"][1]["latest_run"]["suite_name"] == "prod"
    assert body["latest_run"]["results"][0]["case_name"] == (
        "equipment_master_search"
    )
    assert body["latest_run"]["results"][0]["trace"] == {"tool_calls": []}


def test_admin_users_endpoint_hides_pii() -> None:
    fake_admin = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@example.com",
        display_name="Admin",
        avatar_url=None,
        auth_provider="google",
        created_at=datetime.now(UTC),
    )
    app.dependency_overrides[get_current_user] = lambda: fake_admin
    app.dependency_overrides[get_current_admin_user] = lambda: fake_admin
    app.dependency_overrides[get_database_session] = lambda: FakeUsersSession()

    try:
        with TestClient(app) as client:
            response = client.get("/admin/users")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_admin_user, None)
        app.dependency_overrides.pop(get_database_session, None)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"logins", "user_login_counts"}
    assert set(body["logins"][0]) == {"id", "user_id", "created_at"}
    assert set(body["user_login_counts"][0]) == {
        "user_id",
        "login_count",
        "latest_login_at",
    }
