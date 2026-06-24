from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.models import Equipment, WorkOrder


CORRECTIVE_ACTIVITY_TYPES = {
    "corrective",
    "emergency",
    "condition_monitoring",
}

Priority = Literal["low", "medium", "high"]
RoadmapHorizon = Literal["now", "next", "later"]


@dataclass(frozen=True)
class ReliabilityImprovementOpportunity:
    equipment_number: str
    equipment_description: str | None
    equipment_type: str | None
    criticality: str | None
    opportunity_type: str
    priority: Priority
    estimated_annual_value: Decimal
    value_basis: str
    evidence: list[str]


@dataclass(frozen=True)
class ReliabilityImprovementActionPlan:
    equipment_number: str
    title: str
    owner_role: str
    priority: Priority
    actions: list[str]
    milestones: list[str]
    deliverables: list[str]


@dataclass(frozen=True)
class ReliabilityImprovementOutcomeReport:
    equipment_number: str
    success_measures: list[str]
    baseline_summary: str
    expected_outcome: str
    reporting_cadence: str


@dataclass(frozen=True)
class ReliabilityImprovementRoadmapItem:
    equipment_number: str
    title: str
    horizon: RoadmapHorizon
    priority: Priority
    rationale: str
    dependencies: list[str]


class ValueEstimatorTool:
    def run(
        self,
        work_orders: list[WorkOrder],
        limit: int = 5,
    ) -> list[ReliabilityImprovementOpportunity]:
        grouped: dict[str, list[WorkOrder]] = {}

        for work_order in work_orders:
            if work_order.maintenance_activity_type not in CORRECTIVE_ACTIVITY_TYPES:
                continue

            equipment_number = _equipment_number(work_order)
            if equipment_number is None:
                continue

            grouped.setdefault(equipment_number, []).append(work_order)

        opportunities = [
            self._build_opportunity(equipment_work_orders)
            for equipment_work_orders in grouped.values()
        ]

        return sorted(
            opportunities,
            key=lambda item: (
                _priority_score(item.priority),
                item.estimated_annual_value,
                len(item.evidence),
            ),
            reverse=True,
        )[:limit]

    def _build_opportunity(
        self,
        work_orders: list[WorkOrder],
    ) -> ReliabilityImprovementOpportunity:
        first_work_order = work_orders[0]
        equipment = first_work_order.equipment
        equipment_number = _equipment_number(first_work_order) or "unknown"
        total_cost = _sum_decimal(
            work_order.total_cost for work_order in work_orders
        )
        total_downtime = _sum_decimal(
            work_order.downtime_hours for work_order in work_orders
        )
        emergency_count = _count_activity(work_orders, {"emergency"})
        failure_modes = _failure_modes(work_orders)
        repeat_failure_modes = [
            name for name, count in Counter(failure_modes).items() if count >= 2
        ]
        value = (total_cost + (total_downtime * Decimal("1000"))).quantize(
            Decimal("0.01")
        )
        priority = _priority(
            criticality=_equipment_criticality(equipment),
            emergency_count=emergency_count,
            corrective_count=len(work_orders),
            value=value,
            repeat_failure_count=len(repeat_failure_modes),
        )
        opportunity_type = (
            "repeat_failure_elimination"
            if repeat_failure_modes
            else "bad_actor_reliability_improvement"
        )

        return ReliabilityImprovementOpportunity(
            equipment_number=equipment_number,
            equipment_description=_equipment_description(equipment),
            equipment_type=_equipment_type(equipment),
            criticality=_equipment_criticality(equipment),
            opportunity_type=opportunity_type,
            priority=priority,
            estimated_annual_value=value,
            value_basis=(
                f"{len(work_orders)} corrective-like event(s), "
                f"{total_downtime} downtime hour(s), and {total_cost} cost."
            ),
            evidence=[
                work_order.order_number for work_order in work_orders[:5]
            ],
        )


class ActionPlanBuilderTool:
    def run(
        self,
        opportunities: list[ReliabilityImprovementOpportunity],
    ) -> list[ReliabilityImprovementActionPlan]:
        return [
            ReliabilityImprovementActionPlan(
                equipment_number=opportunity.equipment_number,
                title=(
                    "Reliability improvement plan - "
                    f"{opportunity.equipment_number}"
                ),
                owner_role="Reliability Engineer",
                priority=opportunity.priority,
                actions=self._actions(opportunity),
                milestones=[
                    "Confirm scope and baseline evidence.",
                    "Complete investigation and select controls.",
                    "Implement approved corrective and preventive actions.",
                    "Verify effectiveness against the baseline.",
                ],
                deliverables=[
                    "Validated problem statement and evidence pack.",
                    "Approved improvement actions with owners and due dates.",
                    "Post-implementation effectiveness review.",
                ],
            )
            for opportunity in opportunities
        ]

    @staticmethod
    def _actions(
        opportunity: ReliabilityImprovementOpportunity,
    ) -> list[str]:
        if opportunity.opportunity_type == "repeat_failure_elimination":
            return [
                "Open a repeat failure elimination review for the asset.",
                "Validate the dominant failure mode and contributing causes.",
                "Update maintenance strategy or operating controls based on evidence.",
                "Track recurrence, downtime, and cost after implementation.",
            ]

        return [
            "Review the asset as a bad actor with maintenance and operations.",
            "Separate controllable defects from normal operating demand.",
            "Prioritize corrective actions by downtime, cost, and risk reduction.",
            "Track work-order volume, downtime, and cost after implementation.",
        ]


class OutcomeReporterTool:
    def run(
        self,
        opportunities: list[ReliabilityImprovementOpportunity],
    ) -> list[ReliabilityImprovementOutcomeReport]:
        return [
            ReliabilityImprovementOutcomeReport(
                equipment_number=opportunity.equipment_number,
                success_measures=[
                    "Corrective-like work-order count.",
                    "Downtime hours.",
                    "Maintenance cost.",
                    "Repeat failure recurrence.",
                ],
                baseline_summary=opportunity.value_basis,
                expected_outcome=(
                    "Reduce repeat failures, downtime, and avoidable "
                    "maintenance cost against the current baseline."
                ),
                reporting_cadence=(
                    "Review monthly until stable, then include in the "
                    "quarterly reliability review."
                ),
            )
            for opportunity in opportunities
        ]


class RoadmapPlannerTool:
    def run(
        self,
        opportunities: list[ReliabilityImprovementOpportunity],
        action_plans: list[ReliabilityImprovementActionPlan],
    ) -> list[ReliabilityImprovementRoadmapItem]:
        plan_by_equipment = {
            plan.equipment_number: plan for plan in action_plans
        }
        roadmap: list[ReliabilityImprovementRoadmapItem] = []

        for index, opportunity in enumerate(opportunities):
            horizon: RoadmapHorizon = "later"
            if index < 2 or opportunity.priority == "high":
                horizon = "now"
            elif index < 5 or opportunity.priority == "medium":
                horizon = "next"

            plan = plan_by_equipment.get(opportunity.equipment_number)
            roadmap.append(
                ReliabilityImprovementRoadmapItem(
                    equipment_number=opportunity.equipment_number,
                    title=(
                        plan.title
                        if plan is not None
                        else f"Reliability improvement - {opportunity.equipment_number}"
                    ),
                    horizon=horizon,
                    priority=opportunity.priority,
                    rationale=(
                        f"Estimated value {opportunity.estimated_annual_value}; "
                        f"{opportunity.value_basis}"
                    ),
                    dependencies=[
                        "Confirm data quality and operating context.",
                        "Assign owner and agree implementation window.",
                    ],
                )
            )

        return roadmap


def _equipment_number(work_order: WorkOrder) -> str | None:
    if work_order.equipment is not None:
        return work_order.equipment.equipment_number

    return None


def _equipment_description(equipment: Equipment | None) -> str | None:
    return equipment.description if equipment is not None else None


def _equipment_type(equipment: Equipment | None) -> str | None:
    return equipment.equipment_type if equipment is not None else None


def _equipment_criticality(equipment: Equipment | None) -> str | None:
    return equipment.criticality if equipment is not None else None


def _count_activity(
    work_orders: list[WorkOrder],
    activity_types: set[str],
) -> int:
    return sum(
        work_order.maintenance_activity_type in activity_types
        for work_order in work_orders
    )


def _sum_decimal(
    values: Iterable[Decimal | None],
) -> Decimal:
    return sum(
        (value or Decimal("0") for value in values),
        Decimal("0"),
    )


def _failure_modes(work_orders: list[WorkOrder]) -> list[str]:
    modes: list[str] = []

    for work_order in work_orders:
        for link in work_order.failure_mode_links:
            modes.append(link.failure_mode.name)

    return modes


def _priority(
    criticality: str | None,
    emergency_count: int,
    corrective_count: int,
    value: Decimal,
    repeat_failure_count: int,
) -> Priority:
    criticality_score = {
        "critical": 3,
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get((criticality or "").lower(), 0)
    score = (
        criticality_score
        + min(emergency_count, 2)
        + min(corrective_count // 2, 2)
        + min(repeat_failure_count, 2)
    )

    if value >= Decimal("50000"):
        score += 2
    elif value >= Decimal("10000"):
        score += 1

    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"

    return "low"


def _priority_score(priority: Priority) -> int:
    return {
        "high": 3,
        "medium": 2,
        "low": 1,
    }[priority]

