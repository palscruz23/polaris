import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str | None
    openrouter_base_url: str
    openrouter_site_url: str | None
    openrouter_app_name: str
    frontend_url: str | None
    database_url: str
    auth_secret: str
    auth_session_cookie_name: str
    auth_session_days: int
    auth_cookie_secure: bool
    auth_cookie_samesite: str
    auth_redirect_after_login: str
    google_oauth_client_id: str | None
    google_oauth_client_secret: str | None
    google_oauth_redirect_uri: str | None
    microsoft_oauth_client_id: str | None
    microsoft_oauth_client_secret: str | None
    microsoft_oauth_tenant: str
    microsoft_oauth_redirect_uri: str | None
    scheduled_review_teams_webhook_url: str | None
    scheduled_review_teams_destination_label: str
    scheduled_review_default_timezone: str
    admin_emails: tuple[str, ...]


def normalize_optional_url(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().rstrip("/")
    return normalized or None


def build_cors_origins(frontend_url: str | None) -> list[str]:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    normalized_frontend_url = normalize_optional_url(frontend_url)
    if normalized_frontend_url and normalized_frontend_url not in origins:
        origins.append(normalized_frontend_url)
    return origins


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    return int(value)


def _env_csv(name: str) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return ()

    return tuple(
        item.strip().lower()
        for item in value.split(",")
        if item.strip()
    )


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_base_url=os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
        ),
        openrouter_site_url=normalize_optional_url(
            os.getenv("OPENROUTER_SITE_URL")
        ),
        openrouter_app_name=os.getenv(
            "OPENROUTER_APP_NAME",
            "Open Reliability",
        ),
        frontend_url=normalize_optional_url(os.getenv("FRONTEND_URL")),
        database_url=database_url,
        auth_secret=os.getenv(
            "AUTH_SECRET",
            "development-auth-secret-change-me",
        ),
        auth_session_cookie_name=os.getenv(
            "AUTH_SESSION_COOKIE_NAME",
            "polaris_session",
        ),
        auth_session_days=_env_int("AUTH_SESSION_DAYS", 14),
        auth_cookie_secure=_env_bool("AUTH_COOKIE_SECURE", False),
        auth_cookie_samesite=os.getenv(
            "AUTH_COOKIE_SAMESITE",
            "lax",
        ).strip().lower(),
        auth_redirect_after_login=os.getenv(
            "AUTH_REDIRECT_AFTER_LOGIN",
            "http://localhost:3000/chat-with-reliability",
        ),
        google_oauth_client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        google_oauth_redirect_uri=normalize_optional_url(
            os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
        ),
        microsoft_oauth_client_id=os.getenv("MICROSOFT_OAUTH_CLIENT_ID"),
        microsoft_oauth_client_secret=os.getenv(
            "MICROSOFT_OAUTH_CLIENT_SECRET"
        ),
        microsoft_oauth_tenant=os.getenv(
            "MICROSOFT_OAUTH_TENANT",
            "common",
        ),
        microsoft_oauth_redirect_uri=normalize_optional_url(
            os.getenv("MICROSOFT_OAUTH_REDIRECT_URI")
        ),
        scheduled_review_teams_webhook_url=normalize_optional_url(
            os.getenv("SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL")
        ),
        scheduled_review_teams_destination_label=os.getenv(
            "SCHEDULED_REVIEW_TEAMS_DESTINATION_LABEL",
            "Reliability Team",
        ),
        scheduled_review_default_timezone=os.getenv(
            "SCHEDULED_REVIEW_DEFAULT_TIMEZONE",
            "Australia/Sydney",
        ),
        admin_emails=_env_csv("ADMIN_EMAILS"),
    )


settings = load_settings()
