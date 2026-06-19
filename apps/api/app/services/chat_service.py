from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.config import settings
from app.prompts.reliability_agent import RELIABILITY_AGENT_SYSTEM_PROMPT

class ChatServiceError(Exception):
    """Raised when the AI provider cannot produce a response."""

client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    timeout=30.0,
    max_retries=1,
)


def generate_response(message: str) -> str:
    try:
        completion = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {
                    "role": "system",
                    "content": RELIABILITY_AGENT_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
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

    response_content = completion.choices[0].message.content

    if not response_content:
        raise ChatServiceError("The AI provider returned an empty response.")

    return response_content

