import math
from collections.abc import Sequence

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.config import settings
from app.domain.chat import ChatMessage
from app.providers.base import ChatProvider
from app.exceptions import ChatServiceError


class DeepSeekProvider(ChatProvider):
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=30.0,
            max_retries=1,
        )

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def model(self) -> str:
        return settings.deepseek_model

    @property
    def context_window(self) -> int:
        return settings.deepseek_context_window

    def count_tokens(
        self,
        messages: Sequence[ChatMessage],
    ) -> int:
        character_count = sum(
            len(message.role) + len(message.content)
            for message in messages
        )

        return math.ceil(character_count / 3)

    def generate(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
    ) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                    for message in messages
                ],
                max_tokens=max_output_tokens,
                stream=False,
            )
        except APITimeoutError as error:
            raise ChatServiceError(
                "The AI provider took too long to respond."
            ) from error
        except AuthenticationError as error:
            raise ChatServiceError(
                "The AI provider credentials are invalid."
            ) from error
        except RateLimitError as error:
            raise ChatServiceError(
                "The AI provider is currently rate limited."
            ) from error
        except (APIConnectionError, APIStatusError) as error:
            raise ChatServiceError(
                "The AI provider is currently unavailable."
            ) from error

        content = completion.choices[0].message.content

        if not content:
            raise ChatServiceError(
                "The AI provider returned an empty response."
            )

        return content