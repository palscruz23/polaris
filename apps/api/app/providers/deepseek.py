import json
import math
from collections.abc import Sequence
from typing import Any

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
from app.domain.orchestration import (
    AgentModelResponse,
    AgentToolCall,
    AgentToolDefinition,
    AgentToolExchange,
)
from app.exceptions import ChatServiceError
from app.providers.base import ChatProvider


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

    def generate_with_tools(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        tools: Sequence[AgentToolDefinition],
        exchanges: Sequence[AgentToolExchange] = (),
    ) -> AgentModelResponse:
        provider_messages: list[dict[str, Any]] = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in messages
        ]

        for exchange in exchanges:
            provider_messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": exchange.call.id,
                            "type": "function",
                            "function": {
                                "name": exchange.call.name,
                                "arguments": json.dumps(
                                    exchange.call.arguments
                                ),
                            },
                        }
                    ],
                }
            )
            provider_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": exchange.result.call_id,
                    "content": exchange.result.content,
                }
            )

        request: dict[str, Any] = {
            "model": self.model,
            "messages": provider_messages,
            "max_tokens": max_output_tokens,
            "stream": False,
        }

        if tools:
            request["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in tools
            ]
            request["tool_choice"] = "auto"

        try:
            completion = self.client.chat.completions.create(**request)
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

        message = completion.choices[0].message
        tool_calls = tuple(
            self._parse_tool_call(tool_call)
            for tool_call in message.tool_calls or ()
        )

        if not message.content and not tool_calls:
            raise ChatServiceError(
                "The AI provider returned an empty response."
            )

        return AgentModelResponse(
            content=message.content,
            tool_calls=tool_calls,
        )

    @staticmethod
    def _parse_tool_call(tool_call: Any) -> AgentToolCall:
        try:
            arguments = json.loads(tool_call.function.arguments)
        except (json.JSONDecodeError, TypeError) as error:
            raise ChatServiceError(
                "The AI provider returned invalid tool arguments."
            ) from error

        if not isinstance(arguments, dict):
            raise ChatServiceError(
                "The AI provider returned invalid tool arguments."
            )

        return AgentToolCall(
            id=tool_call.id,
            name=tool_call.function.name,
            arguments=arguments,
        )
