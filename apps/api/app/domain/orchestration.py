from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AgentToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class AgentToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AgentToolResult:
    call_id: str
    tool_name: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class AgentToolExchange:
    call: AgentToolCall
    result: AgentToolResult


@dataclass(frozen=True)
class AgentModelResponse:
    content: str | None
    tool_calls: tuple[AgentToolCall, ...] = ()


@dataclass(frozen=True)
class AgentOrchestrationResponse:
    content: str
    tool_calls: tuple[AgentToolExchange, ...] = ()


@dataclass(frozen=True)
class AgentModelCallTrace:
    call_type: str
    status: str
    latency_ms: int
    input_tokens_estimate: int
    output_tokens_estimate: int | None
    max_output_tokens: int
    requested_tool_count: int
    response_tool_call_count: int | None = None
    error_type: str | None = None
    error_message: str | None = None


ModelCallObserver = Callable[[AgentModelCallTrace], None]


@dataclass(frozen=True)
class AgentAnswerReview:
    accepted: bool
    reason: str
    revision_guidance: str | None = None
