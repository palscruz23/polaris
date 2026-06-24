from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.progress import ProgressCallback, report_progress
from app.models import WorkOrder, WorkOrderFailureMode
from app.tools.reliability_improvement import (
    ActionPlanBuilderTool,
    OutcomeReporterTool,
    ReliabilityImprovementActionPlan,
    ReliabilityImprovementOpportunity,
    ReliabilityImprovementOutcomeReport,
    ReliabilityImprovementRoadmapItem,
    RoadmapPlannerTool,
    ValueEstimatorTool,
)


RELIABILITY_IMPROVEMENT_LIMITATIONS = [
    (
        "Value estimates use available work-order cost and downtime only; "
        "lost production, labor constraints, spares availability, and risk "
        "exposure are not fully represented."
    ),
    (
        "Action plans are planning drafts and require site owner confirmation, "
        "engineering review, and approval before execution."
    ),
    (
        "Roadmap sequencing is heuristic and does not yet account for resource "
        "capacity, outage windows, or capital approval gates."
    ),
]


@dataclass(frozen=True)
class ReliabilityImprovementFindings:
    opportunities: list[ReliabilityImprovementOpportunity]
    action_plans: list[ReliabilityImprovementActionPlan]
    outcome_reports: list[ReliabilityImprovementOutcomeReport]
    roadmap: list[ReliabilityImprovementRoadmapItem]
    limitations: list[str]


class ReliabilityImprovementAgent:
    """Specialist agent for reliability improvement planning."""

    def __init__(
        self,
        session: Session,
        value_tool: ValueEstimatorTool | None = None,
        action_plan_tool: ActionPlanBuilderTool | None = None,
        outcome_tool: OutcomeReporterTool | None = None,
        roadmap_tool: RoadmapPlannerTool | None = None,
    ):
        self.session = session
        self.value_tool = value_tool or ValueEstimatorTool()
        self.action_plan_tool = action_plan_tool or ActionPlanBuilderTool()
        self.outcome_tool = outcome_tool or OutcomeReporterTool()
        self.roadmap_tool = roadmap_tool or RoadmapPlannerTool()

    def build_plan(
        self,
        opportunity_limit: int = 5,
        progress: ProgressCallback | None = None,
    ) -> ReliabilityImprovementFindings:
        work_orders = self._load_work_orders()
        report_progress(
            progress,
            stage="tool_started",
            specialist="reliability_improvement",
            tool="value_estimator",
            message=(
                "Reliability Improvement Agent is estimating improvement "
                "opportunities."
            ),
        )
        opportunities = self.value_tool.run(
            work_orders,
            limit=opportunity_limit,
        )
        report_progress(
            progress,
            stage="tool_started",
            specialist="reliability_improvement",
            tool="action_plan_builder",
            message=(
                "Reliability Improvement Agent is drafting action plans."
            ),
        )
        action_plans = self.action_plan_tool.run(opportunities)
        report_progress(
            progress,
            stage="tool_started",
            specialist="reliability_improvement",
            tool="outcome_reporter",
            message=(
                "Reliability Improvement Agent is defining outcome measures."
            ),
        )
        outcome_reports = self.outcome_tool.run(opportunities)
        report_progress(
            progress,
            stage="tool_started",
            specialist="reliability_improvement",
            tool="roadmap_planner",
            message=(
                "Reliability Improvement Agent is sequencing the roadmap."
            ),
        )
        roadmap = self.roadmap_tool.run(opportunities, action_plans)

        return ReliabilityImprovementFindings(
            opportunities=opportunities,
            action_plans=action_plans,
            outcome_reports=outcome_reports,
            roadmap=roadmap,
            limitations=RELIABILITY_IMPROVEMENT_LIMITATIONS,
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
