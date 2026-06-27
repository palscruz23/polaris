from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database import engine
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.services.auth_service import (
    OAuthProfile,
    OAuthRedirectError,
    OAuthStateError,
    build_state_token,
    create_user_session,
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


def test_safe_redirect_path_allows_only_internal_paths() -> None:
    assert safe_redirect_path("/") == "/"
    assert safe_redirect_path("/chat-with-reliability") == (
        "/chat-with-reliability"
    )
    assert safe_redirect_path("https://example.com") is None
    assert safe_redirect_path("//example.com") is None


def test_frontend_redirect_url_uses_frontend_origin_for_internal_path() -> None:
    assert frontend_redirect_url("/") == "http://localhost:3000/"


def test_frontend_redirect_url_rejects_invalid_path() -> None:
    with pytest.raises(OAuthRedirectError):
        frontend_redirect_url("https://example.com")


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

        user_session, token = create_user_session(session, user)
        reloaded_user = get_user_by_session_token(session, token)
        repository = ConversationRepository(session)
        conversation = repository.create("Private chat", user_id=user.id)

        assert user_session.expires_at > datetime.now(UTC) + timedelta(days=13)
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
