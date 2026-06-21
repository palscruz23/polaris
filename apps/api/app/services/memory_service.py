from app.domain.chat import ChatMessage
from app.prompts.conversation_memory import (
    CONVERSATION_MEMORY_COMPACTION_PROMPT,
    CONVERSATION_MEMORY_UPDATE_PROMPT,
)
from app.providers.base import ChatProvider


class MemoryService:
    def __init__(self, provider: ChatProvider):
        self.provider = provider

    def update(
        self,
        previous_memory: str,
        user_message: str,
        assistant_message: str,
    ) -> str:
        messages = [
            ChatMessage(
                role="system",
                content=CONVERSATION_MEMORY_UPDATE_PROMPT,
            ),
            ChatMessage(
                role="user",
                content=(
                    "Previous memory:\n\n"
                    f"{previous_memory or 'No previous memory.'}\n\n"
                    "Latest user message:\n\n"
                    f"{user_message}\n\n"
                    "Latest assistant response:\n\n"
                    f"{assistant_message}"
                ),
            ),
        ]

        return self.provider.generate(
            messages=messages,
            max_output_tokens=min(
                8_000,
                self.provider.context_window // 10,
            ),
        )

    def compact(self, memory_markdown: str) -> str:
        return self.provider.generate(
            messages=[
                ChatMessage(
                    role="system",
                    content=CONVERSATION_MEMORY_COMPACTION_PROMPT,
                ),
                ChatMessage(
                    role="user",
                    content=memory_markdown,
                ),
            ],
            max_output_tokens=min(
                8_000,
                self.provider.context_window // 10,
            ),
        )
