import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin, urlencode, urlparse

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.models.user_session import UserSession

STATE_COOKIE_NAME = "polaris_oauth_state"
REDIRECT_COOKIE_NAME = "polaris_oauth_redirect"


class AuthConfigurationError(RuntimeError):
    pass


class OAuthStateError(RuntimeError):
    pass


class OAuthProviderError(RuntimeError):
    pass


class OAuthRedirectError(RuntimeError):
    pass


@dataclass(frozen=True)
class OAuthProfile:
    provider: str
    subject: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None


def build_state_token() -> str:
    nonce = secrets.token_urlsafe(32)
    signature = _sign(nonce)
    return f"{nonce}.{signature}"


def verify_state_token(expected: str | None, received: str | None) -> None:
    if not expected or not received or not hmac.compare_digest(expected, received):
        raise OAuthStateError("OAuth state did not match.")

    nonce, _, signature = expected.partition(".")
    if not nonce or not signature:
        raise OAuthStateError("OAuth state is invalid.")

    if not hmac.compare_digest(signature, _sign(nonce)):
        raise OAuthStateError("OAuth state signature is invalid.")


def safe_redirect_path(value: str | None) -> str | None:
    if not value:
        return None

    path = value.strip()
    if not path.startswith("/") or path.startswith("//"):
        return None

    return path


def frontend_redirect_url(path: str | None) -> str:
    safe_path = safe_redirect_path(path)
    if safe_path is None:
        raise OAuthRedirectError("OAuth redirect path is invalid.")

    frontend_origin = settings.frontend_url
    if frontend_origin is None:
        parsed_default = urlparse(settings.auth_redirect_after_login)
        if not parsed_default.scheme or not parsed_default.netloc:
            raise OAuthRedirectError("Frontend redirect origin is invalid.")
        frontend_origin = f"{parsed_default.scheme}://{parsed_default.netloc}"

    return urljoin(f"{frontend_origin}/", safe_path.lstrip("/"))


def create_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.auth_session_days)


def google_authorization_url(state: str) -> str:
    if not settings.google_oauth_client_id or not settings.google_oauth_redirect_uri:
        raise AuthConfigurationError("Google OAuth is not configured.")

    query = urlencode(
        {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )

    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def microsoft_authorization_url(state: str) -> str:
    if (
        not settings.microsoft_oauth_client_id
        or not settings.microsoft_oauth_redirect_uri
    ):
        raise AuthConfigurationError("Microsoft OAuth is not configured.")

    tenant = settings.microsoft_oauth_tenant or "common"
    query = urlencode(
        {
            "client_id": settings.microsoft_oauth_client_id,
            "redirect_uri": settings.microsoft_oauth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile User.Read",
            "state": state,
            "response_mode": "query",
            "prompt": "select_account",
        }
    )

    return (
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?"
        f"{query}"
    )


async def exchange_google_code(code: str) -> OAuthProfile:
    if (
        not settings.google_oauth_client_id
        or not settings.google_oauth_client_secret
        or not settings.google_oauth_redirect_uri
    ):
        raise AuthConfigurationError("Google OAuth is not configured.")

    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise OAuthProviderError("Google did not return an access token.")

        profile_response = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        profile_response.raise_for_status()

    profile = profile_response.json()
    subject = profile.get("sub")
    email = profile.get("email")
    if not subject or not email:
        raise OAuthProviderError("Google profile did not include identity data.")

    return OAuthProfile(
        provider="google",
        subject=subject,
        email=email,
        display_name=profile.get("name"),
        avatar_url=profile.get("picture"),
    )


async def exchange_microsoft_code(code: str) -> OAuthProfile:
    if (
        not settings.microsoft_oauth_client_id
        or not settings.microsoft_oauth_client_secret
        or not settings.microsoft_oauth_redirect_uri
    ):
        raise AuthConfigurationError("Microsoft OAuth is not configured.")

    tenant = settings.microsoft_oauth_tenant or "common"
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "code": code,
                "client_id": settings.microsoft_oauth_client_id,
                "client_secret": settings.microsoft_oauth_client_secret,
                "redirect_uri": settings.microsoft_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise OAuthProviderError("Microsoft did not return an access token.")

        profile_response = await client.get(
            "https://graph.microsoft.com/v1.0/me"
            "?$select=id,displayName,mail,userPrincipalName",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        profile_response.raise_for_status()

    profile = profile_response.json()
    subject = profile.get("id")
    email = profile.get("mail") or profile.get("userPrincipalName")
    if not subject or not email:
        raise OAuthProviderError(
            "Microsoft profile did not include identity data."
        )

    return OAuthProfile(
        provider="microsoft",
        subject=subject,
        email=email,
        display_name=profile.get("displayName"),
    )


def upsert_oauth_user(session: Session, profile: OAuthProfile) -> User:
    statement = select(User).where(
        User.auth_provider == profile.provider,
        User.provider_subject == profile.subject,
    )
    user = session.scalar(statement)

    if user is None:
        user = User(
            email=profile.email,
            display_name=profile.display_name,
            avatar_url=profile.avatar_url,
            auth_provider=profile.provider,
            provider_subject=profile.subject,
        )
        session.add(user)
    else:
        user.email = profile.email
        user.display_name = profile.display_name
        user.avatar_url = profile.avatar_url

    session.commit()
    session.refresh(user)
    return user


def create_user_session(session: Session, user: User) -> tuple[UserSession, str]:
    token = create_session_token()
    user_session = UserSession(
        user_id=user.id,
        session_token_hash=hash_session_token(token),
        expires_at=session_expires_at(),
    )
    session.add(user_session)
    session.commit()
    session.refresh(user_session)

    return user_session, token


def get_user_by_session_token(session: Session, token: str | None) -> User | None:
    if not token:
        return None

    now = datetime.now(UTC)
    statement = (
        select(UserSession)
        .join(UserSession.user)
        .where(
            UserSession.session_token_hash == hash_session_token(token),
            UserSession.expires_at > now,
            User.is_active.is_(True),
        )
    )
    user_session = session.scalar(statement)
    if user_session is None:
        return None

    user_session.last_seen_at = now
    session.commit()
    return user_session.user


def delete_session_token(session: Session, token: str | None) -> None:
    if not token:
        return

    session.execute(
        delete(UserSession).where(
            UserSession.session_token_hash == hash_session_token(token)
        )
    )
    session.commit()


def _sign(value: str) -> str:
    return hmac.new(
        settings.auth_secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
