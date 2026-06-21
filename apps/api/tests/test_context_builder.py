import math
from collections.abc import Sequence

from app.domain.chat import ChatMessage
from app.providers.base import ChatProvider
from app.services.context_builder import ContextBuilder


class EstimatingProvider(ChatProvider):
    @property
    def name(self) -> str:
        return "test"

    @property
    def model(self) -> str:
        return "test-model"

    @property
    def context_window(self) -> int:
        return 300

    def count_tokens(
        self,
        messages: Sequence[ChatMessage],
    ) -> int:
        return math.ceil(
            sum(len(message.role) + len(message.content) for message in messages)
            / 3
        )

    def generate(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
    ) -> str:
        raise NotImplementedError


def test_context_builder_selects_newest_complete_turns() -> None:
    provider = EstimatingProvider()
    builder = ContextBuilder(provider)
    history = [
        ChatMessage(role="user", content="Old question " * 10),
        ChatMessage(role="assistant", content="Old answer " * 10),
        ChatMessage(role="user", content="Recent question"),
        ChatMessage(role="assistant", content="Recent answer"),
        ChatMessage(role="user", content="Incomplete question"),
    ]

    result = builder.build(
        system_prompt="System",
        memory_markdown="Memory",
        history=history,
        current_user_message="Current question",
    )

    contents = [message.content for message in result.messages]

    assert "Recent question" in contents
    assert "Recent answer" in contents
    assert "Incomplete question" not in contents
    assert contents[-1] == "Current question"
