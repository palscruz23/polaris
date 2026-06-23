from app.providers.base import ChatProvider
from app.providers.models import get_available_model
from app.providers.openrouter import OpenRouterProvider


def get_chat_provider(model_id: str | None = None) -> ChatProvider:
    return OpenRouterProvider(get_available_model(model_id))
