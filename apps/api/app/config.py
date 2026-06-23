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
        openrouter_site_url=os.getenv("OPENROUTER_SITE_URL"),
        openrouter_app_name=os.getenv(
            "OPENROUTER_APP_NAME",
            "Open Reliability",
        ),
        frontend_url=normalize_optional_url(os.getenv("FRONTEND_URL")),
        database_url=database_url,
    )


settings = load_settings()
