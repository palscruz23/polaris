from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.models import Equipment, WorkOrder


CORRECTIVE_ACTIVITY_TYPES = {
    "corrective",
    "emergency",
    "condition_monitoring",
}
REPAIR_ACTIVITY_TYPES = {
    "corrective",
    "emergency",
}
PREVENTIVE_ACTIVITY_TYPES = {
    "preventive",
    "inspection",
}


@dataclass(frozen=True)
class DefectEliminationDatasetSummary:
    total_work_orders: int
    corrective_work_orders: int
    emergency_work_orders: int
    preventive_work_orders: int
    condition_monitoring_work_orders: int
    total_cost: Decimal
    total_downtime_hours: Decimal
    first_work_order_at: datetime | None
    last_work_order_at: datetime | None
    corrective_preventive_ratio: Decimal | None


@dataclass(frozen=True)
class BadActorFinding:
    equipment_number: str
    equipment_description: str | None
    equipment_type: str | None
    functional_location: str | None
    criticality: str | None
    total_work_orders: int
    corrective_work_orders: int
    emergency_work_orders: int
    preventive_work_orders: int
    total_cost: Decimal
    total_downtime_hours: Decimal
    mttr_hours: Decimal | None
    corrective_event_count: int
    observation_days: Decimal | None
    mtbf_days: Decimal | None
    first_event_at: datetime | None
    last_event_at: datetime | None
    score: Decimal


@dataclass(frozen=True)
class RepeatFailureFinding:
    equipment_number: str
    equipment_description: str | None
    failure_mode: str
    equipment_type: str | None
    work_order_count: int
    total_cost: Decimal
    total_downtime_hours: Decimal
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    evidence: str


@dataclass(frozen=True)
class FailureModeBadActorFinding:
    equipment_number: str
    equipment_description: str | None
    failure_mode: str
    equipment_type: str | None
    repeat_work_order_count: int
    total_cost: Decimal
    total_downtime_hours: Decimal
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    evidence: str
    score: Decimal


class BadActorAnalysisTool:
    def run(
        self,
        work_orders: list[WorkOrder],
        limit: int = 10,
    ) -> list[BadActorFinding]:
        grouped: dict[str, list[WorkOrder]] = {}

        for work_order in work_orders:
            equipment_number = _equipment_number(work_order)
            if equipment_number is None:
                continue

            grouped.setdefault(equipment_number, []).append(work_order)

        findings = [
            self._build_finding(equipment_number, equipment_work_orders)
            for equipment_number, equipment_work_orders in grouped.items()
        ]

        return sorted(
            findings,
            key=lambda finding: (
                finding.mtbf_days is not None,
                -(finding.mtbf_days or Decimal("0")),
                finding.corrective_event_count,
                finding.total_downtime_hours,
                finding.total_cost,
            ),
            reverse=True,
        )[:limit]

    def _build_finding(
        self,
        equipment_number: str,
        work_orders: list[WorkOrder],
    ) -> BadActorFinding:
        first_work_order = work_orders[0]
        equipment = first_work_order.equipment
        corrective_count = _count_activity(work_orders, CORRECTIVE_ACTIVITY_TYPES)
        emergency_count = _count_activity(work_orders, {"emergency"})
        preventive_count = _count_activity(work_orders, PREVENTIVE_ACTIVITY_TYPES)
        repair_count = _count_activity(work_orders, REPAIR_ACTIVITY_TYPES)
        total_cost = _sum_decimal(work_order.total_cost for work_order in work_orders)
        total_downtime = _sum_decimal(
            work_order.downtime_hours for work_order in work_orders
        )
        repair_event_dates = _repair_event_dates(work_orders)
        observation_days = _observation_days(repair_event_dates)
        mtbf_days = (
            _safe_divide_decimal(
                observation_days,
                Decimal(len(repair_event_dates) - 1),
            )
            if observation_days is not None
            else None
        )
        mttr = _safe_divide(total_downtime, repair_count)
        score = _mtbf_bad_actor_score(mtbf_days, repair_count)

        return BadActorFinding(
            equipment_number=equipment_number,
            equipment_description=_equipment_description(equipment),
            equipment_type=_equipment_type(equipment),
            functional_location=first_work_order.functional_location
            or _equipment_functional_location(equipment),
            criticality=_equipment_criticality(equipment),
            total_work_orders=len(work_orders),
            corrective_work_orders=corrective_count,
            emergency_work_orders=emergency_count,
            preventive_work_orders=preventive_count,
            total_cost=total_cost,
            total_downtime_hours=total_downtime,
            mttr_hours=mttr,
            corrective_event_count=repair_count,
            observation_days=observation_days,
            mtbf_days=mtbf_days,
            first_event_at=repair_event_dates[0] if repair_event_dates else None,
            last_event_at=repair_event_dates[-1] if repair_event_dates else None,
            score=score,
        )


class RepeatFailureDetectionTool:
    def run(
        self,
        work_orders: list[WorkOrder],
        minimum_occurrences: int = 2,
        limit: int = 10,
    ) -> list[RepeatFailureFinding]:
        grouped: dict[tuple[str, str], list[WorkOrder]] = {}

        for work_order in work_orders:
            equipment_number = _equipment_number(work_order)
            if equipment_number is None:
                continue

            for link in work_order.failure_mode_links:
                failure_mode_name = link.failure_mode.name
                grouped.setdefault(
                    (equipment_number, failure_mode_name),
                    [],
                ).append(work_order)

        findings = [
            self._build_finding(equipment_number, failure_mode, grouped_work_orders)
            for (equipment_number, failure_mode), grouped_work_orders in grouped.items()
            if len(grouped_work_orders) >= minimum_occurrences
        ]

        return sorted(
            findings,
            key=lambda finding: (
                finding.work_order_count,
                finding.total_downtime_hours,
                finding.total_cost,
            ),
            reverse=True,
        )[:limit]

    def _build_finding(
        self,
        equipment_number: str,
        failure_mode: str,
        work_orders: list[WorkOrder],
    ) -> RepeatFailureFinding:
        first_work_order = work_orders[0]
        equipment = first_work_order.equipment
        dates = [
            work_order.finished_at or work_order.created_at_source
            for work_order in work_orders
            if work_order.finished_at or work_order.created_at_source
        ]
        total_cost = _sum_decimal(work_order.total_cost for work_order in work_orders)
        total_downtime = _sum_decimal(
            work_order.downtime_hours for work_order in work_orders
        )

        return RepeatFailureFinding(
            equipment_number=equipment_number,
            equipment_description=_equipment_description(equipment),
            failure_mode=failure_mode,
            equipment_type=_equipment_type(equipment),
            work_order_count=len(work_orders),
            total_cost=total_cost,
            total_downtime_hours=total_downtime,
            first_seen_at=min(dates) if dates else None,
            last_seen_at=max(dates) if dates else None,
            evidence=", ".join(
                work_order.order_number for work_order in work_orders[:5]
            ),
        )


class FailureModeBadActorAnalysisTool:
    def run(
        self,
        repeat_failures: list[RepeatFailureFinding],
        limit: int = 10,
    ) -> list[FailureModeBadActorFinding]:
        findings = [
            FailureModeBadActorFinding(
                equipment_number=finding.equipment_number,
                equipment_description=finding.equipment_description,
                failure_mode=finding.failure_mode,
                equipment_type=finding.equipment_type,
                repeat_work_order_count=finding.work_order_count,
                total_cost=finding.total_cost,
                total_downtime_hours=finding.total_downtime_hours,
                first_seen_at=finding.first_seen_at,
                last_seen_at=finding.last_seen_at,
                evidence=finding.evidence,
                score=_failure_mode_bad_actor_score(finding),
            )
            for finding in repeat_failures
        ]

        return sorted(
            findings,
            key=lambda finding: (
                finding.repeat_work_order_count,
                finding.total_downtime_hours,
                finding.total_cost,
            ),
            reverse=True,
        )[:limit]


class ReliabilityMetricsTool:
    def summarize(
        self,
        work_orders: list[WorkOrder],
    ) -> DefectEliminationDatasetSummary:
        dates = [
            work_order.finished_at or work_order.created_at_source
            for work_order in work_orders
            if work_order.finished_at or work_order.created_at_source
        ]
        corrective_count = _count_activity(work_orders, {"corrective"})
        emergency_count = _count_activity(work_orders, {"emergency"})
        preventive_count = _count_activity(work_orders, PREVENTIVE_ACTIVITY_TYPES)
        condition_monitoring_count = _count_activity(
            work_orders,
            {"condition_monitoring"},
        )
        corrective_like_count = _count_activity(
            work_orders,
            CORRECTIVE_ACTIVITY_TYPES,
        )

        return DefectEliminationDatasetSummary(
            total_work_orders=len(work_orders),
            corrective_work_orders=corrective_count,
            emergency_work_orders=emergency_count,
            preventive_work_orders=preventive_count,
            condition_monitoring_work_orders=condition_monitoring_count,
            total_cost=_sum_decimal(
                work_order.total_cost for work_order in work_orders
            ),
            total_downtime_hours=_sum_decimal(
                work_order.downtime_hours for work_order in work_orders
            ),
            first_work_order_at=min(dates) if dates else None,
            last_work_order_at=max(dates) if dates else None,
            corrective_preventive_ratio=_safe_divide(
                Decimal(corrective_like_count),
                preventive_count,
            ),
        )


def _equipment_number(work_order: WorkOrder) -> str | None:
    if work_order.equipment is not None:
        return work_order.equipment.equipment_number

    return None


def _equipment_description(equipment: Equipment | None) -> str | None:
    return equipment.description if equipment is not None else None


def _equipment_type(equipment: Equipment | None) -> str | None:
    return equipment.equipment_type if equipment is not None else None


def _equipment_functional_location(equipment: Equipment | None) -> str | None:
    return equipment.functional_location if equipment is not None else None


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


def _sum_decimal(values: object) -> Decimal:
    total = Decimal("0")

    for value in values:
        if value is not None:
            total += value

    return total


def _repair_event_dates(work_orders: list[WorkOrder]) -> list[datetime]:
    return sorted(
        work_order.finished_at or work_order.created_at_source
        for work_order in work_orders
        if work_order.maintenance_activity_type in REPAIR_ACTIVITY_TYPES
        and (work_order.finished_at or work_order.created_at_source)
    )


def _observation_days(dates: list[datetime]) -> Decimal | None:
    if len(dates) < 2:
        return None

    elapsed_seconds = Decimal(str((dates[-1] - dates[0]).total_seconds()))
    return (elapsed_seconds / Decimal("86400")).quantize(Decimal("0.01"))


def _mtbf_bad_actor_score(
    mtbf_days: Decimal | None,
    repair_count: int,
) -> Decimal:
    if mtbf_days is None:
        return Decimal("0")

    mtbf_floor = max(mtbf_days, Decimal("0.01"))
    return ((Decimal(repair_count) * Decimal("100")) / mtbf_floor).quantize(
        Decimal("0.01")
    )


def _failure_mode_bad_actor_score(
    finding: RepeatFailureFinding,
) -> Decimal:
    return (
        (Decimal(finding.work_order_count) * Decimal("100"))
        + finding.total_downtime_hours
        + (finding.total_cost / Decimal("1000"))
    ).quantize(Decimal("0.01"))


def _safe_divide(
    numerator: Decimal,
    denominator: int,
) -> Decimal | None:
    if denominator == 0:
        return None

    return (numerator / Decimal(denominator)).quantize(Decimal("0.01"))


def _safe_divide_decimal(
    numerator: Decimal,
    denominator: Decimal,
) -> Decimal | None:
    if denominator == 0:
        return None

    return (numerator / denominator).quantize(Decimal("0.01"))
