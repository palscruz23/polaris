from dataclasses import dataclass
from typing import Literal

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


ReliabilityImprovementIntent = Literal[
    "full_improvement_plan",
    "estimate_opportunities",
    "build_action_plans",
    "define_outcomes",
    "plan_roadmap",
]


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
        return self.analyze(
            intent="full_improvement_plan",
            opportunity_limit=opportunity_limit,
            progress=progress,
        )

    def analyze(
        self,
        intent: ReliabilityImprovementIntent = "full_improvement_plan",
        equipment_numbers: list[str] | None = None,
        opportunity_limit: int = 5,
        progress: ProgressCallback | None = None,
    ) -> ReliabilityImprovementFindings:
        work_orders = self._load_work_orders()
        work_orders = self._filter_work_orders(work_orders, equipment_numbers)
        opportunities = self._estimate_opportunities(
            work_orders,
            opportunity_limit,
            progress,
        )

        if intent == "estimate_opportunities":
            return self._findings(opportunities=opportunities)

        action_plans = self._build_action_plans(opportunities, progress)

        if intent == "build_action_plans":
            return self._findings(
                opportunities=opportunities,
                action_plans=action_plans,
            )

        outcome_reports = self._define_outcomes(opportunities, progress)

        if intent == "define_outcomes":
            return self._findings(
                opportunities=opportunities,
                action_plans=action_plans,
                outcome_reports=outcome_reports,
            )

        roadmap = self._plan_roadmap(opportunities, action_plans, progress)

        return self._findings(
            opportunities=opportunities,
            action_plans=action_plans,
            outcome_reports=outcome_reports,
            roadmap=roadmap,
        )

    def _estimate_opportunities(
        self,
        work_orders: list[WorkOrder],
        opportunity_limit: int,
        progress: ProgressCallback | None,
    ) -> list[ReliabilityImprovementOpportunity]:
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
        return self.value_tool.run(
            work_orders,
            limit=opportunity_limit,
        )

    def _build_action_plans(
        self,
        opportunities: list[ReliabilityImprovementOpportunity],
        progress: ProgressCallback | None,
    ) -> list[ReliabilityImprovementActionPlan]:
        report_progress(
            progress,
            stage="tool_started",
            specialist="reliability_improvement",
            tool="action_plan_builder",
            message=(
                "Reliability Improvement Agent is drafting action plans."
            ),
        )
        return self.action_plan_tool.run(opportunities)

    def _define_outcomes(
        self,
        opportunities: list[ReliabilityImprovementOpportunity],
        progress: ProgressCallback | None,
    ) -> list[ReliabilityImprovementOutcomeReport]:
        report_progress(
            progress,
            stage="tool_started",
            specialist="reliability_improvement",
            tool="outcome_reporter",
            message=(
                "Reliability Improvement Agent is defining outcome measures."
            ),
        )
        return self.outcome_tool.run(opportunities)

    def _plan_roadmap(
        self,
        opportunities: list[ReliabilityImprovementOpportunity],
        action_plans: list[ReliabilityImprovementActionPlan],
        progress: ProgressCallback | None,
    ) -> list[ReliabilityImprovementRoadmapItem]:
        report_progress(
            progress,
            stage="tool_started",
            specialist="reliability_improvement",
            tool="roadmap_planner",
            message=(
                "Reliability Improvement Agent is sequencing the roadmap."
            ),
        )
        return self.roadmap_tool.run(opportunities, action_plans)

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

    @staticmethod
    def _findings(
        *,
        opportunities: list[ReliabilityImprovementOpportunity] | None = None,
        action_plans: list[ReliabilityImprovementActionPlan] | None = None,
        outcome_reports: list[ReliabilityImprovementOutcomeReport]
        | None = None,
        roadmap: list[ReliabilityImprovementRoadmapItem] | None = None,
    ) -> ReliabilityImprovementFindings:
        return ReliabilityImprovementFindings(
            opportunities=opportunities or [],
            action_plans=action_plans or [],
            outcome_reports=outcome_reports or [],
            roadmap=roadmap or [],
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
