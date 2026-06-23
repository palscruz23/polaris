from dataclasses import dataclass
from typing import Any


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
