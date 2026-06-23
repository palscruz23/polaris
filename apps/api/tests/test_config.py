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
