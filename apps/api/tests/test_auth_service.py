import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.database import engine
from app.models.user import User
from app.models.user_login_event import UserLoginEvent
from app.models.user_session import UserSession
from app.repositories.conversation_repository import ConversationRepository
from app.services.auth_service import (
    OAuthProfile,
    OAuthRedirectError,
    OAuthStateError,
    build_state_token,
    create_user_session,
    delete_session_token,
    frontend_redirect_url,
    get_user_by_session_token,
    hash_session_token,
    safe_redirect_path,
    upsert_oauth_user,
    verify_state_token,
)


def test_oauth_state_token_round_trip() -> None:
    state = build_state_token()

    verify_state_token(state, state)


def test_oauth_state_token_rejects_mismatch() -> None:
    state = build_state_token()

    try:
        verify_state_token(state, "different-state")
    except OAuthStateError:
        pass
    else:
        raise AssertionError("Expected OAuthStateError.")


def test_session_token_is_hashed() -> None:
    token = "session-token"

    assert hash_session_token(token) != token
    assert hash_session_token(token) == hash_session_token(token)


class FakeAuthSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False
        self.refreshed: list[object] = []

    def add(self, model: object) -> None:
        self.added.append(model)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, model: object) -> None:
        self.refreshed.append(model)


def test_safe_redirect_path_allows_only_internal_paths() -> None:
    assert safe_redirect_path("/") == "/"
    assert safe_redirect_path("/ask-polaris") == "/ask-polaris"
    assert safe_redirect_path("https://example.com") is None
    assert safe_redirect_path("//example.com") is None


def test_frontend_redirect_url_uses_frontend_origin_for_internal_path() -> None:
    assert frontend_redirect_url("/") == "http://localhost:3000/"


def test_frontend_redirect_url_rejects_invalid_path() -> None:
    with pytest.raises(OAuthRedirectError):
        frontend_redirect_url("https://example.com")


def test_create_user_session_records_login_event() -> None:
    user = User(
        id=uuid.UUID("8eb47798-1232-457a-90ad-93b336d5b56e"),
        email="user@example.com",
        auth_provider="google",
        provider_subject="google-user-1",
    )
    session = FakeAuthSession()

    user_session, token = create_user_session(session, user)  # type: ignore[arg-type]

    assert token
    assert user_session.user_id == user.id
    assert session.committed is True
    assert session.refreshed == [user_session]
    assert [type(model) for model in session.added] == [
        UserSession,
        UserLoginEvent,
    ]
    assert session.added[1].user_id == user.id


def test_oauth_user_session_and_conversation_scoping() -> None:
    try:
        connection = engine.connect()
    except OperationalError as error:
        pytest.skip(f"Postgres is unavailable: {error}")

    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        user = upsert_oauth_user(
            session,
            OAuthProfile(
                provider="google",
                subject="google-user-1",
                email="user@example.com",
                display_name="Reliability User",
            ),
        )
        other_user = User(
            email="other@example.com",
            auth_provider="google",
            provider_subject="google-user-2",
        )
        session.add(other_user)
        session.commit()
        session.refresh(other_user)

        try:
            user_session, token = create_user_session(session, user)
        except ProgrammingError as error:
            if "user_login_events" in str(error):
                pytest.skip("Postgres schema is missing user_login_events.")
            raise
        reloaded_user = get_user_by_session_token(session, token)
        repository = ConversationRepository(session)
        conversation = repository.create("Private chat", user_id=user.id)

        assert user_session.expires_at > datetime.now(UTC) + timedelta(days=13)
        assert len(user.login_events) == 1
        assert reloaded_user is not None
        assert reloaded_user.id == user.id
        assert repository.get_by_id(conversation.id, user_id=user.id) is not None
        assert repository.get_by_id(
            conversation.id,
            user_id=other_user.id,
        ) is None
        assert repository.list_recent(user_id=user.id) == [conversation]
        assert repository.list_recent(user_id=other_user.id) == []
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_logout_removes_active_session_but_keeps_login_history() -> None:
    try:
        connection = engine.connect()
    except OperationalError as error:
        pytest.skip(f"Postgres is unavailable: {error}")

    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        user = upsert_oauth_user(
            session,
            OAuthProfile(
                provider="google",
                subject="google-user-login-history",
                email="history@example.com",
                display_name="Login History",
            ),
        )
        try:
            _, token = create_user_session(session, user)
        except ProgrammingError as error:
            if "user_login_events" in str(error):
                pytest.skip("Postgres schema is missing user_login_events.")
            raise

        delete_session_token(session, token)

        session_count = session.query(UserSession).filter_by(
            user_id=user.id,
        ).count()
        login_count = session.query(UserLoginEvent).filter_by(
            user_id=user.id,
        ).count()

        assert session_count == 0
        assert login_count == 1
    finally:
        session.close()
        transaction.rollback()
        connection.close()
