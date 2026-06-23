import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.models import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL_ID,
    get_available_model,
)


def test_models_endpoint_returns_only_supported_models() -> None:
    with TestClient(app) as client:
        response = client.get("/models")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": model.id,
            "label": model.label,
            "is_default": model.id == DEFAULT_MODEL_ID,
            "is_enabled": model.enabled,
        }
        for model in AVAILABLE_MODELS
    ]


def test_default_model_is_deepseek_v4_flash() -> None:
    selected_model = get_available_model(None)

    assert selected_model.id == "deepseek/deepseek-v4-flash"
    assert selected_model.label == "DeepSeek V4 Flash"


def test_unknown_model_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="The selected model is not available.",
    ):
        get_available_model("provider/unknown-model")


def test_production_model_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="The selected model is reserved for production use.",
    ):
        get_available_model("openai/gpt-5.5")
