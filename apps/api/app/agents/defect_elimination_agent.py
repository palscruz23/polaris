from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import WorkOrder, WorkOrderFailureMode
from app.tools.defect_elimination import (
    BadActorAnalysisTool,
    BadActorFinding,
    DefectEliminationCharter,
    DefectEliminationCharterGeneratorTool,
    DefectEliminationDatasetSummary,
    FiveWhysAnalysis,
    FiveWhysGeneratorTool,
    MTBFFinding,
    MTBFCalculationTool,
    RCAEvidencePlan,
    RCAEvidencePlanningTool,
    RCATemplate,
    RCATemplateBuilderTool,
    ReliabilityMetricsTool,
    RepeatFailureDetectionTool,
    RepeatFailureFinding,
)


@dataclass(frozen=True)
class DefectEliminationFindings:
    summary: DefectEliminationDatasetSummary
    bad_actors: list[BadActorFinding]
    repeat_failures: list[RepeatFailureFinding]
    mtbf_metrics: list[MTBFFinding]
    rca_evidence_plans: list[RCAEvidencePlan]
    five_whys: list[FiveWhysAnalysis]
    rca_templates: list[RCATemplate]
    charters: list[DefectEliminationCharter]
    recommendations: list[str]


class DefectEliminationAgent:
    """Specialist agent for repeat failure and bad actor investigations."""

    def __init__(
        self,
        session: Session,
        bad_actor_tool: BadActorAnalysisTool | None = None,
        repeat_failure_tool: RepeatFailureDetectionTool | None = None,
        metrics_tool: ReliabilityMetricsTool | None = None,
        mtbf_tool: MTBFCalculationTool | None = None,
        rca_evidence_tool: RCAEvidencePlanningTool | None = None,
        five_whys_tool: FiveWhysGeneratorTool | None = None,
        rca_template_tool: RCATemplateBuilderTool | None = None,
        charter_tool: DefectEliminationCharterGeneratorTool | None = None,
    ):
        self.session = session
        self.bad_actor_tool = bad_actor_tool or BadActorAnalysisTool()
        self.repeat_failure_tool = (
            repeat_failure_tool or RepeatFailureDetectionTool()
        )
        self.metrics_tool = metrics_tool or ReliabilityMetricsTool()
        self.mtbf_tool = mtbf_tool or MTBFCalculationTool()
        self.rca_evidence_tool = rca_evidence_tool or RCAEvidencePlanningTool()
        self.five_whys_tool = five_whys_tool or FiveWhysGeneratorTool()
        self.rca_template_tool = rca_template_tool or RCATemplateBuilderTool()
        self.charter_tool = charter_tool or DefectEliminationCharterGeneratorTool()

    def build_overview(
        self,
        bad_actor_limit: int = 10,
        repeat_failure_limit: int = 10,
        minimum_repeat_occurrences: int = 2,
    ) -> DefectEliminationFindings:
        work_orders = self._load_work_orders()
        summary = self.metrics_tool.summarize(work_orders)
        bad_actors = self.bad_actor_tool.run(
            work_orders,
            limit=bad_actor_limit,
        )
        repeat_failures = self.repeat_failure_tool.run(
            work_orders,
            minimum_occurrences=minimum_repeat_occurrences,
            limit=repeat_failure_limit,
        )
        mtbf_metrics = self.mtbf_tool.run(
            work_orders,
            limit=bad_actor_limit,
        )
        rca_evidence_plans = self.rca_evidence_tool.run(repeat_failures)
        five_whys = self.five_whys_tool.run(repeat_failures)
        rca_templates = self.rca_template_tool.run(repeat_failures)
        charters = self.charter_tool.run(
            repeat_failures=repeat_failures,
            mtbf_metrics=mtbf_metrics,
            evidence_plans=rca_evidence_plans,
            five_whys=five_whys,
        )

        return DefectEliminationFindings(
            summary=summary,
            bad_actors=bad_actors,
            repeat_failures=repeat_failures,
            mtbf_metrics=mtbf_metrics,
            rca_evidence_plans=rca_evidence_plans,
            five_whys=five_whys,
            rca_templates=rca_templates,
            charters=charters,
            recommendations=self._build_recommendations(
                bad_actors,
                repeat_failures,
                mtbf_metrics,
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

    def _build_recommendations(
        self,
        bad_actors: list[BadActorFinding],
        repeat_failures: list[RepeatFailureFinding],
        mtbf_metrics: list[MTBFFinding],
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

        if repeat_failures:
            top_repeat = repeat_failures[0]
            recommendations.append(
                "Open a repeat failure investigation for "
                f"{top_repeat.equipment_number} / {top_repeat.failure_mode}; "
                f"the pattern appears in {top_repeat.work_order_count} work "
                "orders."
            )

        if mtbf_metrics:
            shortest_mtbf = mtbf_metrics[0]
            if shortest_mtbf.mtbf_days is not None:
                recommendations.append(
                    "Validate operating context and maintenance controls for "
                    f"{shortest_mtbf.equipment_number}; it has an estimated "
                    f"MTBF of {shortest_mtbf.mtbf_days} days across "
                    f"{shortest_mtbf.corrective_event_count} repair events."
                )

        if not recommendations:
            recommendations.append(
                "No repeat failure pattern meets the current threshold. Review "
                "data scope or lower the occurrence threshold if needed."
            )

        return recommendations
