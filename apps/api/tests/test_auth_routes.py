import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database import get_database_session
from app.main import app
from app.routes import auth
from app.services.auth_service import (
    REDIRECT_COOKIE_NAME,
    STATE_COOKIE_NAME,
    OAuthProfile,
    build_state_token,
)


class FakeSession:
    pass


def test_google_login_sets_state_and_safe_redirect_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_states: list[str] = []

    def authorization_url(state: str) -> str:
        captured_states.append(state)
        return f"https://provider.example/login?state={state}"

    monkeypatch.setattr(auth, "google_authorization_url", authorization_url)

    with TestClient(app) as client:
        response = client.get(
            "/auth/google/login?next=/admin",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert response.headers["location"].startswith(
        "https://provider.example/login"
    )
    assert captured_states
    assert response.cookies[STATE_COOKIE_NAME] == captured_states[0]
    assert response.cookies[REDIRECT_COOKIE_NAME].strip('"') == "/admin"
    assert "HttpOnly" in response.headers["set-cookie"]


def test_google_login_ignores_external_next_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth,
        "google_authorization_url",
        lambda state: f"https://provider.example/login?state={state}",
    )

    with TestClient(app) as client:
        response = client.get(
            "/auth/google/login?next=https://evil.example",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert REDIRECT_COOKIE_NAME not in response.cookies


def test_google_callback_creates_session_cookie_and_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = build_state_token()
    calls: dict[str, object] = {}
    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        email="user@example.com",
        display_name="Reliability User",
        avatar_url=None,
        auth_provider="google",
        created_at=datetime.now(UTC),
    )

    async def exchange_profile(code: str) -> OAuthProfile:
        calls["code"] = code
        return OAuthProfile(
            provider="google",
            subject="google-user",
            email="user@example.com",
            display_name="Reliability User",
        )

    def upsert_user(session: object, profile: OAuthProfile) -> object:
        calls["session"] = session
        calls["profile"] = profile
        return fake_user

    def create_session(session: object, user: object) -> tuple[object, str]:
        calls["session_user"] = user
        return object(), "plain-session-token"

    monkeypatch.setattr(auth, "exchange_google_code", exchange_profile)
    monkeypatch.setattr(auth, "upsert_oauth_user", upsert_user)
    monkeypatch.setattr(auth, "create_user_session", create_session)
    app.dependency_overrides[get_database_session] = lambda: FakeSession()

    try:
        with TestClient(app) as client:
            client.cookies.set(STATE_COOKIE_NAME, state)
            client.cookies.set(
                REDIRECT_COOKIE_NAME,
                "/ask-polaris",
            )
            response = client.get(
                "/auth/google/callback?code=oauth-code&state=" + state,
                follow_redirects=False,
            )
    finally:
        app.dependency_overrides.pop(get_database_session, None)

    assert response.status_code == 307
    assert response.headers["location"] == "http://localhost:3000/ask-polaris"
    assert response.cookies["polaris_session"] == "plain-session-token"
    assert calls["code"] == "oauth-code"
    assert calls["session_user"] == fake_user


def test_google_callback_defaults_to_homepage_when_next_cookie_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = build_state_token()
    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        email="user@example.com",
        display_name="Reliability User",
        avatar_url=None,
        auth_provider="google",
        created_at=datetime.now(UTC),
    )

    async def exchange_profile(code: str) -> OAuthProfile:
        del code
        return OAuthProfile(
            provider="google",
            subject="google-user",
            email="user@example.com",
            display_name="Reliability User",
        )

    monkeypatch.setattr(auth, "exchange_google_code", exchange_profile)
    monkeypatch.setattr(auth, "upsert_oauth_user", lambda _s, _p: fake_user)
    monkeypatch.setattr(
        auth,
        "create_user_session",
        lambda _s, _u: (object(), "plain-session-token"),
    )
    app.dependency_overrides[get_database_session] = lambda: FakeSession()

    try:
        with TestClient(app) as client:
            client.cookies.set(STATE_COOKIE_NAME, state)
            response = client.get(
                "/auth/google/callback?code=oauth-code&state=" + state,
                follow_redirects=False,
            )
    finally:
        app.dependency_overrides.pop(get_database_session, None)

    assert response.status_code == 307
    assert response.headers["location"] == "http://localhost:3000/"


def test_google_callback_rejects_invalid_state() -> None:
    with TestClient(app) as client:
        client.cookies.set(STATE_COOKIE_NAME, "expected")
        response = client.get(
            "/auth/google/callback?code=oauth-code&state=received",
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "OAuth state did not match."
