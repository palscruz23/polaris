from collections.abc import Callable
from dataclasses import dataclass, field

from app.domain.orchestration import SubToolCall


@dataclass(frozen=True)
class OrchestrationProgress:
    stage: str
    message: str
    specialist: str | None = None
    tool: str | None = None


ProgressCallback = Callable[[OrchestrationProgress], None]


def report_progress(
    callback: ProgressCallback | None,
    *,
    stage: str,
    message: str,
    specialist: str | None = None,
    tool: str | None = None,
) -> None:
    if callback is None:
        return

    callback(
        OrchestrationProgress(
            stage=stage,
            message=message,
            specialist=specialist,
            tool=tool,
        )
    )


class ToolCallCollector:
    """Wraps a ProgressCallback and collects tool_started events.

    Each ``tool_started`` event that carries a *specialist* and *tool* is
    recorded as a `.SubToolCall`.  The collector forwards every event to the
    optional *inner* callback so live SSE progress is unaffected.
    """

    def __init__(self, inner: ProgressCallback | None = None) -> None:
        self._inner = inner
        self.sub_calls: list[SubToolCall] = []

    def __call__(self, progress: OrchestrationProgress) -> None:
        if (
            progress.stage == "tool_started"
            and progress.specialist
            and progress.tool
        ):
            self.sub_calls.append(
                SubToolCall(
                    specialist=progress.specialist,
                    tool=progress.tool,
                    message=progress.message,
                )
            )
        if self._inner is not None:
            self._inner(progress)
