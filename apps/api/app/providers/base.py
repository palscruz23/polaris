from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.chat import ChatMessage


class ChatProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the configured model identifier."""

    @property
    @abstractmethod
    def context_window(self) -> int:
        """Return the model context-window size in tokens."""

    @abstractmethod
    def count_tokens(
        self,
        messages: Sequence[ChatMessage],
    ) -> int:
        """Count or conservatively estimate tokens."""

    @abstractmethod
    def generate(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
    ) -> str:
        """Generate an assistant response."""