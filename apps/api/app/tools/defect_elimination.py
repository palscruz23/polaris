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
class FailureInvestigationFinding:
    equipment_number: str
    equipment_description: str | None
    failure_mode: str
    equipment_type: str | None
    work_order_count: int
    evidence: str | None = None


@dataclass(frozen=True)
class MTBFFinding:
    equipment_number: str
    equipment_description: str | None
    equipment_type: str | None
    corrective_event_count: int
    observation_days: Decimal | None
    mtbf_days: Decimal | None
    first_event_at: datetime | None
    last_event_at: datetime | None


@dataclass(frozen=True)
class RCAEvidencePlan:
    equipment_number: str
    failure_mode: str
    evidence_to_collect: list[str]
    people_to_interview: list[str]
    records_to_review: list[str]
    immediate_containment_actions: list[str]


@dataclass(frozen=True)
class FiveWhysAnalysis:
    equipment_number: str
    failure_mode: str
    problem_statement: str
    whys: list[str]
    likely_root_cause_theme: str


@dataclass(frozen=True)
class RCATemplate:
    equipment_number: str
    failure_mode: str
    title: str
    sections: list[str]
    starter_questions: list[str]


@dataclass(frozen=True)
class DefectEliminationCharter:
    equipment_number: str
    failure_mode: str
    title: str
    problem_statement: str
    business_impact: str
    asset_context: str
    failure_pattern_summary: str
    hypotheses: list[str]
    required_evidence: list[str]
    recommended_actions: list[str]
    success_criteria: list[str]
    verification_plan: list[str]


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


class MTBFCalculationTool:
    def run(
        self,
        work_orders: list[WorkOrder],
        limit: int = 10,
    ) -> list[MTBFFinding]:
        grouped: dict[str, list[WorkOrder]] = {}

        for work_order in work_orders:
            if work_order.maintenance_activity_type not in REPAIR_ACTIVITY_TYPES:
                continue

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
                finding.mtbf_days or Decimal("0"),
            ),
        )[:limit]

    def _build_finding(
        self,
        equipment_number: str,
        work_orders: list[WorkOrder],
    ) -> MTBFFinding:
        first_work_order = work_orders[0]
        equipment = first_work_order.equipment
        dates = _repair_event_dates(work_orders)
        observation_days = _observation_days(dates)
        mtbf_days = None

        if observation_days is not None:
            mtbf_days = _safe_divide_decimal(
                observation_days,
                Decimal(len(dates) - 1),
            )

        return MTBFFinding(
            equipment_number=equipment_number,
            equipment_description=_equipment_description(equipment),
            equipment_type=_equipment_type(equipment),
            corrective_event_count=len(work_orders),
            observation_days=observation_days,
            mtbf_days=mtbf_days,
            first_event_at=dates[0] if dates else None,
            last_event_at=dates[-1] if dates else None,
        )


class RCAEvidencePlanningTool:
    def run(
        self,
        repeat_failures: list[RepeatFailureFinding],
        limit: int = 5,
    ) -> list[RCAEvidencePlan]:
        return [
            self._build_plan(repeat_failure)
            for repeat_failure in repeat_failures[:limit]
        ]

    def _build_plan(
        self,
        repeat_failure: RepeatFailureFinding,
    ) -> RCAEvidencePlan:
        equipment_type = repeat_failure.equipment_type or "equipment"

        return RCAEvidencePlan(
            equipment_number=repeat_failure.equipment_number,
            failure_mode=repeat_failure.failure_mode,
            evidence_to_collect=[
                f"Photos or inspection notes showing {repeat_failure.failure_mode}.",
                f"Operating conditions before each {equipment_type} failure event.",
                "Maintenance execution notes, parts replaced, and measured condition.",
                "Recent alarms, trips, vibration, temperature, or process trend data.",
            ],
            people_to_interview=[
                "Operator who observed the failure or abnormal condition.",
                "Maintainer who completed the repair.",
                "Reliability or maintenance engineer responsible for the asset.",
                "Planner or scheduler if maintenance timing may be a contributor.",
            ],
            records_to_review=[
                f"Linked work orders: {repeat_failure.evidence}.",
                "Preventive maintenance history and skipped/deferred tasks.",
                "OEM manual or site maintenance standard for the failure mode.",
                "Spares history and component replacement records.",
            ],
            immediate_containment_actions=[
                "Confirm the asset is safe to continue operating.",
                "Check whether sister assets have the same symptoms.",
                "Raise a short-term inspection or monitoring task until root cause is known.",
            ],
        )


class FiveWhysGeneratorTool:
    def run(
        self,
        failures: list[FailureInvestigationFinding | RepeatFailureFinding],
        limit: int = 5,
    ) -> list[FiveWhysAnalysis]:
        return [
            self._build_analysis(self._to_investigation(failure))
            for failure in failures[:limit]
        ]

    def run_for_failure(
        self,
        equipment_number: str,
        failure_mode: str,
        equipment_type: str | None = None,
        equipment_description: str | None = None,
        work_order_count: int = 1,
        evidence: str | None = None,
    ) -> FiveWhysAnalysis:
        return self._build_analysis(
            FailureInvestigationFinding(
                equipment_number=equipment_number,
                equipment_description=equipment_description,
                failure_mode=failure_mode,
                equipment_type=equipment_type,
                work_order_count=work_order_count,
                evidence=evidence,
            )
        )

    def _build_analysis(
        self,
        failure: FailureInvestigationFinding,
    ) -> FiveWhysAnalysis:
        equipment_type = failure.equipment_type or "asset"
        failure_mode = failure.failure_mode

        return FiveWhysAnalysis(
            equipment_number=failure.equipment_number,
            failure_mode=failure_mode,
            problem_statement=self._problem_statement(failure),
            whys=[
                f"Why did the {equipment_type} experience {failure_mode}?",
                "Why was the failure mechanism not detected or corrected earlier?",
                "Why did the current maintenance strategy not prevent recurrence?",
                "Why were operating, installation, or maintenance conditions allowed to persist?",
                "Why is there no effective control that verifies the root cause has been removed?",
            ],
            likely_root_cause_theme=(
                "Likely theme to validate: maintenance strategy gap, operating "
                "condition issue, installation/quality issue, or ineffective "
                "previous corrective action."
            ),
        )

    def _to_investigation(
        self,
        failure: FailureInvestigationFinding | RepeatFailureFinding,
    ) -> FailureInvestigationFinding:
        if isinstance(failure, FailureInvestigationFinding):
            return failure

        return FailureInvestigationFinding(
            equipment_number=failure.equipment_number,
            equipment_description=failure.equipment_description,
            failure_mode=failure.failure_mode,
            equipment_type=failure.equipment_type,
            work_order_count=failure.work_order_count,
            evidence=failure.evidence,
        )

    def _problem_statement(
        self,
        failure: FailureInvestigationFinding,
    ) -> str:
        if failure.work_order_count > 1:
            return (
                f"{failure.equipment_number} has repeated {failure.failure_mode} "
                f"events across {failure.work_order_count} work orders."
            )

        if failure.evidence:
            return (
                f"{failure.equipment_number} has a {failure.failure_mode} "
                f"failure event requiring RCA. Evidence: {failure.evidence}."
            )

        return (
            f"{failure.equipment_number} has a {failure.failure_mode} "
            "failure event requiring RCA."
        )


class RCATemplateBuilderTool:
    def run(
        self,
        failures: list[FailureInvestigationFinding | RepeatFailureFinding],
        limit: int = 5,
    ) -> list[RCATemplate]:
        return [
            self._build_template(self._to_investigation(failure))
            for failure in failures[:limit]
        ]

    def run_for_failure(
        self,
        equipment_number: str,
        failure_mode: str,
        equipment_type: str | None = None,
        equipment_description: str | None = None,
        work_order_count: int = 1,
        evidence: str | None = None,
    ) -> RCATemplate:
        return self._build_template(
            FailureInvestigationFinding(
                equipment_number=equipment_number,
                equipment_description=equipment_description,
                failure_mode=failure_mode,
                equipment_type=equipment_type,
                work_order_count=work_order_count,
                evidence=evidence,
            )
        )

    def _build_template(
        self,
        failure: FailureInvestigationFinding,
    ) -> RCATemplate:
        return RCATemplate(
            equipment_number=failure.equipment_number,
            failure_mode=failure.failure_mode,
            title=(
                "RCA - "
                f"{failure.equipment_number} "
                f"{failure.failure_mode}"
            ),
            sections=[
                "Problem statement",
                "Asset and operating context",
                "Event timeline",
                "Failure mode and consequence",
                "Evidence collected",
                "5 Whys or causal analysis",
                "Root cause statement",
                "Corrective and preventive actions",
                "Verification plan",
                "Owner, due date, and closeout criteria",
            ],
            starter_questions=self._starter_questions(failure),
        )

    def _to_investigation(
        self,
        failure: FailureInvestigationFinding | RepeatFailureFinding,
    ) -> FailureInvestigationFinding:
        if isinstance(failure, FailureInvestigationFinding):
            return failure

        return FailureInvestigationFinding(
            equipment_number=failure.equipment_number,
            equipment_description=failure.equipment_description,
            failure_mode=failure.failure_mode,
            equipment_type=failure.equipment_type,
            work_order_count=failure.work_order_count,
            evidence=failure.evidence,
        )

    def _starter_questions(
        self,
        failure: FailureInvestigationFinding,
    ) -> list[str]:
        equipment_type = failure.equipment_type or "asset"
        first_question = (
            "What changed before the first event in the repeat pattern?"
            if failure.work_order_count > 1
            else (
                f"What changed before the {equipment_type} "
                f"experienced {failure.failure_mode}?"
            )
        )

        questions = [
            first_question,
            "What evidence confirms the failure mode rather than only the symptom?",
            "Which current PM or condition-monitoring task should have detected this?",
        ]

        if failure.work_order_count > 1:
            questions.append(
                "Were previous corrective actions completed and verified effective?"
            )

        questions.append("What permanent control will prevent recurrence?")
        return questions


class DefectEliminationCharterGeneratorTool:
    def run(
        self,
        repeat_failures: list[RepeatFailureFinding],
        mtbf_metrics: list[MTBFFinding],
        evidence_plans: list[RCAEvidencePlan],
        five_whys: list[FiveWhysAnalysis],
        limit: int = 3,
    ) -> list[DefectEliminationCharter]:
        mtbf_by_equipment = {
            finding.equipment_number: finding for finding in mtbf_metrics
        }
        evidence_by_pattern = {
            (plan.equipment_number, plan.failure_mode): plan
            for plan in evidence_plans
        }
        five_whys_by_pattern = {
            (analysis.equipment_number, analysis.failure_mode): analysis
            for analysis in five_whys
        }

        return [
            self._build_charter(
                repeat_failure=repeat_failure,
                mtbf=mtbf_by_equipment.get(repeat_failure.equipment_number),
                evidence_plan=evidence_by_pattern.get(
                    (
                        repeat_failure.equipment_number,
                        repeat_failure.failure_mode,
                    )
                ),
                five_whys=five_whys_by_pattern.get(
                    (
                        repeat_failure.equipment_number,
                        repeat_failure.failure_mode,
                    )
                ),
            )
            for repeat_failure in repeat_failures[:limit]
        ]

    def _build_charter(
        self,
        repeat_failure: RepeatFailureFinding,
        mtbf: MTBFFinding | None,
        evidence_plan: RCAEvidencePlan | None,
        five_whys: FiveWhysAnalysis | None,
    ) -> DefectEliminationCharter:
        mtbf_context = (
            f" Estimated MTBF is {mtbf.mtbf_days} days across "
            f"{mtbf.corrective_event_count} repair events."
            if mtbf is not None and mtbf.mtbf_days is not None
            else " MTBF could not be calculated from the available event dates."
        )
        required_evidence = (
            evidence_plan.evidence_to_collect
            if evidence_plan is not None
            else ["Confirm failure mode evidence from work order history."]
        )
        root_cause_theme = (
            five_whys.likely_root_cause_theme
            if five_whys is not None
            else (
                "Likely theme to validate: maintenance strategy gap, operating "
                "condition issue, installation/quality issue, or ineffective "
                "previous corrective action."
            )
        )

        return DefectEliminationCharter(
            equipment_number=repeat_failure.equipment_number,
            failure_mode=repeat_failure.failure_mode,
            title=(
                "Defect Elimination Charter - "
                f"{repeat_failure.equipment_number} "
                f"{repeat_failure.failure_mode}"
            ),
            problem_statement=(
                f"{repeat_failure.equipment_number} has repeated "
                f"{repeat_failure.failure_mode} across "
                f"{repeat_failure.work_order_count} work orders between "
                f"{_format_datetime(repeat_failure.first_seen_at)} and "
                f"{_format_datetime(repeat_failure.last_seen_at)}."
            ),
            business_impact=(
                f"The repeat pattern has accumulated "
                f"{repeat_failure.total_downtime_hours} downtime hours and "
                f"{repeat_failure.total_cost} in recorded maintenance cost."
                f"{mtbf_context}"
            ),
            asset_context=(
                f"Equipment: {repeat_failure.equipment_number}. "
                f"Description: {repeat_failure.equipment_description or 'Not recorded'}. "
                f"Equipment type: {repeat_failure.equipment_type or 'Not recorded'}."
            ),
            failure_pattern_summary=(
                f"Repeat pattern: {repeat_failure.failure_mode}. Evidence work "
                f"orders: {repeat_failure.evidence}."
            ),
            hypotheses=[
                "The current maintenance strategy does not control the dominant failure mode.",
                "Operating conditions may be accelerating the failure mechanism.",
                "Previous corrective actions may have restored function without removing root cause.",
                root_cause_theme,
            ],
            required_evidence=required_evidence,
            recommended_actions=[
                "Assign an owner for the defect elimination investigation.",
                "Validate the failure mode with physical evidence and work order history.",
                "Complete RCA using the evidence plan and 5 Whys prompts.",
                "Define corrective actions that remove or control the verified root cause.",
                "Add a verification check to confirm recurrence has reduced after implementation.",
            ],
            success_criteria=[
                "No recurrence of the same failure mode for the agreed monitoring period.",
                "Corrective work order count decreases for the target asset.",
                "Downtime and maintenance cost trend down after actions are implemented.",
                "Updated PM, operating, or condition-monitoring control is documented and owned.",
            ],
            verification_plan=[
                "Review new work orders weekly for recurrence of the same failure mode.",
                "Track downtime, cost, and repair count for the target asset.",
                "Confirm corrective actions are completed and effectiveness is checked.",
                "Close the charter only after recurrence criteria are met.",
            ],
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


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "an unknown date"

    return value.date().isoformat()
