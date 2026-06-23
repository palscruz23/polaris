from collections.abc import Callable
from dataclasses import dataclass


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
