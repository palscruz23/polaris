class ChatServiceError(Exception):
    """Raised when the AI provider cannot produce a response."""


class ContextBudgetError(Exception):
    """Raised when required context cannot fit the provider token budget."""


class MemoryCompactionRequired(ContextBudgetError):
    """Raised when conversation memory exceeds its allocated token budget."""


class ConversationNotFoundError(Exception):
    """Raised when a requested conversation does not exist."""


class ConversationBusyError(Exception):
    """Raised when a conversation already has an active response."""
