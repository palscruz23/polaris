from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.progress import ProgressCallback, report_progress
from app.models import WorkOrder, WorkOrderFailureMode
from app.tools.defect_elimination import (
    BadActorAnalysisTool,
    BadActorFinding,
    DefectEliminationDatasetSummary,
    FailureModeBadActorAnalysisTool,
    FailureModeBadActorFinding,
    ReliabilityMetricsTool,
    RepeatFailureDetectionTool,
    RepeatFailureFinding,
)


@dataclass(frozen=True)
class DefectEliminationFindings:
    summary: DefectEliminationDatasetSummary
    bad_actors: list[BadActorFinding]
    repeat_failures: list[RepeatFailureFinding]
    failure_mode_bad_actors: list[FailureModeBadActorFinding]
    recommendations: list[str]


DefectEliminationIntent = Literal[
    "overview",
    "rank_bad_actors",
    "find_repeat_failures",
    "rank_failure_mode_bad_actors",
]


class DefectEliminationAgent:
    """Specialist agent for repeat failure and bad actor investigations."""

    def __init__(
        self,
        session: Session,
        bad_actor_tool: BadActorAnalysisTool | None = None,
        failure_mode_bad_actor_tool: FailureModeBadActorAnalysisTool
        | None = None,
        repeat_failure_tool: RepeatFailureDetectionTool | None = None,
        metrics_tool: ReliabilityMetricsTool | None = None,
    ):
        self.session = session
        self.bad_actor_tool = bad_actor_tool or BadActorAnalysisTool()
        self.failure_mode_bad_actor_tool = (
            failure_mode_bad_actor_tool or FailureModeBadActorAnalysisTool()
        )
        self.repeat_failure_tool = (
            repeat_failure_tool or RepeatFailureDetectionTool()
        )
        self.metrics_tool = metrics_tool or ReliabilityMetricsTool()

    def build_overview(
        self,
        bad_actor_limit: int = 10,
        repeat_failure_limit: int = 10,
        minimum_repeat_occurrences: int = 2,
        progress: ProgressCallback | None = None,
    ) -> DefectEliminationFindings:
        return self.analyze(
            intent="overview",
            bad_actor_limit=bad_actor_limit,
            repeat_failure_limit=repeat_failure_limit,
            minimum_repeat_occurrences=minimum_repeat_occurrences,
            progress=progress,
        )

    def analyze(
        self,
        intent: DefectEliminationIntent = "overview",
        equipment_numbers: list[str] | None = None,
        bad_actor_limit: int = 10,
        repeat_failure_limit: int = 10,
        minimum_repeat_occurrences: int = 2,
        progress: ProgressCallback | None = None,
    ) -> DefectEliminationFindings:
        work_orders = self._load_work_orders()
        work_orders = self._filter_work_orders(work_orders, equipment_numbers)
        report_progress(
            progress,
            stage="tool_started",
            specialist="defect_elimination",
            tool="reliability_metrics",
            message=(
                "Defect Elimination Agent is summarizing the reliability "
                "history."
            ),
        )
        summary = self.metrics_tool.summarize(work_orders)

        if intent == "rank_bad_actors":
            bad_actors = self._rank_bad_actors(
                work_orders,
                bad_actor_limit,
                progress,
            )
            return self._findings(
                summary=summary,
                bad_actors=bad_actors,
                recommendations=self._build_recommendations(
                    bad_actors,
                    [],
                    [],
                ),
            )

        if intent == "find_repeat_failures":
            repeat_failures = self._detect_repeat_failures(
                work_orders,
                repeat_failure_limit,
                minimum_repeat_occurrences,
                progress,
            )
            return self._findings(
                summary=summary,
                repeat_failures=repeat_failures,
                recommendations=self._build_recommendations(
                    [],
                    repeat_failures,
                    [],
                ),
            )

        if intent == "rank_failure_mode_bad_actors":
            repeat_failures = self._detect_repeat_failures(
                work_orders,
                repeat_failure_limit,
                minimum_repeat_occurrences,
                progress,
            )
            failure_mode_bad_actors = self._rank_failure_mode_bad_actors(
                repeat_failures,
                bad_actor_limit,
                progress,
            )
            return self._findings(
                summary=summary,
                repeat_failures=repeat_failures,
                failure_mode_bad_actors=failure_mode_bad_actors,
                recommendations=self._build_recommendations(
                    [],
                    repeat_failures,
                    failure_mode_bad_actors,
                ),
            )

        bad_actors = self._rank_bad_actors(
            work_orders,
            bad_actor_limit,
            progress,
        )
        repeat_failures = self._detect_repeat_failures(
            work_orders,
            repeat_failure_limit,
            minimum_repeat_occurrences,
            progress,
        )
        failure_mode_bad_actors = self._rank_failure_mode_bad_actors(
            repeat_failures,
            bad_actor_limit,
            progress,
        )

        return DefectEliminationFindings(
            summary=summary,
            bad_actors=bad_actors,
            repeat_failures=repeat_failures,
            failure_mode_bad_actors=failure_mode_bad_actors,
            recommendations=self._build_recommendations(
                bad_actors,
                repeat_failures,
                failure_mode_bad_actors,
            ),
        )

    def _load_work_orders(self) -> list[WorkOrder]:
        statement = (
            select(WorkOrder)
            .options(
                selectinload(WorkOrder.equipment),
                selectinload(WorkOrder.failure_mode_links)
                .selectinload(WorkOrderFailureMode.failure_mode),
            )
            .order_by(WorkOrder.finished_at.desc().nullslast())
        )

        return list(self.session.scalars(statement).all())

    @staticmethod
    def _filter_work_orders(
        work_orders: list[WorkOrder],
        equipment_numbers: list[str] | None,
    ) -> list[WorkOrder]:
        if not equipment_numbers:
            return work_orders

        requested = set(equipment_numbers)
        return [
            work_order
            for work_order in work_orders
            if work_order.equipment is not None
            and work_order.equipment.equipment_number in requested
        ]

    def _rank_bad_actors(
        self,
        work_orders: list[WorkOrder],
        limit: int,
        progress: ProgressCallback | None,
    ) -> list[BadActorFinding]:
        report_progress(
            progress,
            stage="tool_started",
            specialist="defect_elimination",
            tool="bad_actor_analysis",
            message="Defect Elimination Agent is identifying bad actors.",
        )
        return self.bad_actor_tool.run(work_orders, limit=limit)

    def _detect_repeat_failures(
        self,
        work_orders: list[WorkOrder],
        limit: int,
        minimum_occurrences: int,
        progress: ProgressCallback | None,
    ) -> list[RepeatFailureFinding]:
        report_progress(
            progress,
            stage="tool_started",
            specialist="defect_elimination",
            tool="repeat_failure_detection",
            message=(
                "Defect Elimination Agent is checking repeat failures."
            ),
        )
        return self.repeat_failure_tool.run(
            work_orders,
            minimum_occurrences=minimum_occurrences,
            limit=limit,
        )

    def _rank_failure_mode_bad_actors(
        self,
        repeat_failures: list[RepeatFailureFinding],
        limit: int,
        progress: ProgressCallback | None,
    ) -> list[FailureModeBadActorFinding]:
        report_progress(
            progress,
            stage="tool_started",
            specialist="defect_elimination",
            tool="failure_mode_bad_actor_analysis",
            message=(
                "Defect Elimination Agent is ranking bad actors by repeated "
                "equipment failure modes."
            ),
        )
        return self.failure_mode_bad_actor_tool.run(
            repeat_failures,
            limit=limit,
        )

    @staticmethod
    def _findings(
        *,
        summary: DefectEliminationDatasetSummary,
        bad_actors: list[BadActorFinding] | None = None,
        repeat_failures: list[RepeatFailureFinding] | None = None,
        failure_mode_bad_actors: list[FailureModeBadActorFinding]
        | None = None,
        recommendations: list[str] | None = None,
    ) -> DefectEliminationFindings:
        return DefectEliminationFindings(
            summary=summary,
            bad_actors=bad_actors or [],
            repeat_failures=repeat_failures or [],
            failure_mode_bad_actors=failure_mode_bad_actors or [],
            recommendations=recommendations or [],
        )

    def _build_recommendations(
        self,
        bad_actors: list[BadActorFinding],
        repeat_failures: list[RepeatFailureFinding],
        failure_mode_bad_actors: list[FailureModeBadActorFinding],
    ) -> list[str]:
        recommendations: list[str] = []

        if bad_actors:
            top_bad_actor = bad_actors[0]
            if top_bad_actor.mtbf_days is not None:
                recommendations.append(
                    "Prioritize a defect elimination review for "
                    f"{top_bad_actor.equipment_number}; it has an estimated "
                    f"MTBF of {top_bad_actor.mtbf_days} days across "
                    f"{top_bad_actor.corrective_event_count} repair events."
                )
            else:
                recommendations.append(
                    "Prioritize a defect elimination review for "
                    f"{top_bad_actor.equipment_number}; it has "
                    f"{top_bad_actor.corrective_work_orders} corrective-like work "
                    "orders and "
                    f"{top_bad_actor.total_downtime_hours} downtime hours."
                )

        if failure_mode_bad_actors:
            top_failure_mode = failure_mode_bad_actors[0]
            recommendations.append(
                "Prioritize the recurring failure mode "
                f"{top_failure_mode.equipment_number} / "
                f"{top_failure_mode.failure_mode}; it appears in "
                f"{top_failure_mode.repeat_work_order_count} work orders with "
                f"{top_failure_mode.total_downtime_hours} downtime hours."
            )

        if repeat_failures:
            top_repeat = repeat_failures[0]
            recommendations.append(
                "Open a repeat failure investigation for "
                f"{top_repeat.equipment_number} / {top_repeat.failure_mode}; "
                f"the pattern appears in {top_repeat.work_order_count} work "
                "orders."
            )

        if not recommendations:
            recommendations.append(
                "No repeat failure pattern meets the current threshold. Review "
                "data scope or lower the occurrence threshold if needed."
            )

        return recommendations
