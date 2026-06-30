import os

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/polaris-watch-task2-test.db")

from app.config import build_cors_origins, normalize_optional_url


def test_normalize_optional_url_removes_whitespace_and_trailing_slash() -> None:
    assert (
        normalize_optional_url(" https://open-reliability.vercel.app/ ")
        == "https://open-reliability.vercel.app"
    )


def test_normalize_optional_url_returns_none_for_empty_values() -> None:
    assert normalize_optional_url(None) is None
    assert normalize_optional_url("") is None
    assert normalize_optional_url(" / ") is None


def test_build_cors_origins_includes_local_and_deployed_frontends() -> None:
    assert build_cors_origins("https://open-reliability.vercel.app/") == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://open-reliability.vercel.app",
    ]


def test_build_cors_origins_does_not_duplicate_local_frontend() -> None:
    assert build_cors_origins("http://localhost:3000/") == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_polaris_watch_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@host/db")
    monkeypatch.setenv("OPENROUTER_SITE_URL", "https://open-reliability.vercel.app/")
    monkeypatch.setenv(
        "SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL",
        "https://example.test/teams",
    )
    monkeypatch.setenv(
        "SCHEDULED_REVIEW_TEAMS_DESTINATION_LABEL",
        "Reliability Standup",
    )
    monkeypatch.setenv("SCHEDULED_REVIEW_DEFAULT_TIMEZONE", "Australia/Perth")

    from app.config import load_settings

    loaded = load_settings()

    assert loaded.openrouter_site_url == "https://open-reliability.vercel.app"
    assert loaded.scheduled_review_teams_webhook_url == "https://example.test/teams"
    assert loaded.scheduled_review_teams_destination_label == "Reliability Standup"
    assert loaded.scheduled_review_default_timezone == "Australia/Perth"
