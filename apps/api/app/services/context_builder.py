from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.chat import ChatMessage
from app.exceptions import ContextBudgetError, MemoryCompactionRequired
from app.providers.base import ChatProvider


@dataclass(frozen=True)
class ContextBuildResult:
    messages: list[ChatMessage]
    max_output_tokens: int
    history_tokens: int
    memory_tokens: int


class ContextBuilder:
    def __init__(self, provider: ChatProvider):
        self.provider = provider

    def build(
        self,
        system_prompt: str,
        memory_markdown: str,
        history: Sequence[ChatMessage],
        current_user_message: str,
    ) -> ContextBuildResult:
        context_window = self.provider.context_window

        max_output_tokens = min(
            8_000,
            context_window // 4,
        )
        safety_margin_tokens = context_window // 20
        memory_limit_tokens = context_window // 10

        system_message = ChatMessage(
            role="system",
            content=system_prompt,
        )
        current_message = ChatMessage(
            role="user",
            content=current_user_message,
        )

        system_tokens = self.provider.count_tokens([system_message])
        current_message_tokens = self.provider.count_tokens([current_message])

        memory_message = self._build_memory_message(
            memory_markdown=memory_markdown,
            memory_limit_tokens=memory_limit_tokens,
        )
        memory_tokens = self.provider.count_tokens([memory_message])

        history_budget = (
            context_window
            - max_output_tokens
            - safety_margin_tokens
            - system_tokens
            - memory_tokens
            - current_message_tokens
        )

        if history_budget < 0:
            raise ContextBudgetError(
                "System prompt, memory, and current message exceed the context budget."
            )

        selected_history = self._select_history(
            history=history,
            history_budget=history_budget,
        )

        history_tokens = self.provider.count_tokens(selected_history)

        return ContextBuildResult(
            messages=[
                system_message,
                memory_message,
                *selected_history,
                current_message,
            ],
            max_output_tokens=max_output_tokens,
            history_tokens=history_tokens,
            memory_tokens=memory_tokens,
        )

    def _build_memory_message(
        self,
        memory_markdown: str,
        memory_limit_tokens: int,
    ) -> ChatMessage:
        memory_message = ChatMessage(
            role="system",
            content=(
                "Conversation memory:\n\n"
                f"{memory_markdown or 'No durable conversation memory yet.'}"
            ),
        )

        if self.provider.count_tokens([memory_message]) > memory_limit_tokens:
            raise MemoryCompactionRequired(
                "Conversation memory exceeds its token budget and requires compaction."
            )

        return memory_message

    def _select_history(
        self,
        history: Sequence[ChatMessage],
        history_budget: int,
    ) -> list[ChatMessage]:
        turns = self._group_complete_turns(history)
        selected_turns: list[list[ChatMessage]] = []
        used_tokens = 0

        for turn in reversed(turns):
            turn_tokens = self.provider.count_tokens(turn)

            if used_tokens + turn_tokens > history_budget:
                break

            selected_turns.append(turn)
            used_tokens += turn_tokens

        selected_turns.reverse()

        return [
            message
            for turn in selected_turns
            for message in turn
        ]

    @staticmethod
    def _group_complete_turns(
        history: Sequence[ChatMessage],
    ) -> list[list[ChatMessage]]:
        turns: list[list[ChatMessage]] = []
        pending_user_message: ChatMessage | None = None

        for message in history:
            if message.role == "user":
                pending_user_message = message
                continue

            if (
                message.role == "assistant"
                and pending_user_message is not None
            ):
                turns.append([pending_user_message, message])
                pending_user_message = None

        return turns
