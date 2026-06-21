from functools import lru_cache

from app.providers.base import ChatProvider
from app.providers.deepseek import DeepSeekProvider


@lru_cache(maxsize=1)
def get_chat_provider() -> ChatProvider:
    return DeepSeekProvider()
