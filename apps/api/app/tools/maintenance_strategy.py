import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.models import Equipment, MaintenanceStrategy, WorkOrder
from app.tools.defect_elimination import (
    RepeatFailureDetectionTool,
    RepeatFailureFinding,
)

CORRECTIVE_TYPES = {"corrective", "emergency", "condition_monitoring"}
TOKEN_STOP_WORDS = {
    "and",
    "asset",
    "check",
    "condition",
    "failure",
    "for",
    "inspect",
    "inspection",
    "maintenance",
    "monitor",
    "of",
    "the",
}

CoverageStatus = Literal["covered", "partial", "uncovered"]
RiskLevel = Literal["low", "medium", "high", "unknown"]
RecommendationAction = Literal["keep", "modify", "add", "engineering_review"]


@dataclass(frozen=True)
class MaintenanceStrategyTaskProfile:
    strategy_number: str | None
    task_number: str | None
    task_description: str
    strategy_type: str
    frequency_value: Decimal | None
    frequency_unit: str | None
    frequency_days: Decimal | None
    status: str


@dataclass(frozen=True)
class MaintenanceStrategyProfile:
    equipment_number: str
    equipment_description: str | None
    equipment_type: str | None
    criticality: str | None
    task_count: int
    active_task_count: int
    strategy_types: list[str]
    tasks: list[MaintenanceStrategyTaskProfile]


@dataclass(frozen=True)
class MaintenanceMix:
    total_work_orders: int
    corrective_work_orders: int
    emergency_work_orders: int
    preventive_work_orders: int
    inspection_work_orders: int
    condition_monitoring_work_orders: int
    corrective_preventive_ratio: Decimal | None
    total_cost: Decimal
    total_downtime_hours: Decimal


@dataclass(frozen=True)
class FailureModeCoverage:
    failure_mode: str
    occurrence_count: int
    coverage: CoverageStatus
    matched_task_numbers: list[str]
    matched_task_descriptions: list[str]
    confidence: Literal["low", "medium", "high"]
    evidence_work_orders: list[str]
    is_repeat_failure: bool
    repeat_failure_work_order_count: int | None
    repeat_failure_total_cost: Decimal | None
    repeat_failure_total_downtime_hours: Decimal | None
    repeat_failure_evidence: str | None


@dataclass(frozen=True)
class FrequencyRisk:
    task_number: str | None
    task_description: str
    frequency_days: Decimal | None
    related_failure_modes: list[str]
    observed_recurrence_days: Decimal | None
    risk: RiskLevel
    reason: str


@dataclass(frozen=True)
class MaintenanceStrategyGap:
    gap_type: str
    failure_mode: str | None
    severity: RiskLevel
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class MaintenanceStrategyRecommendation:
    action: RecommendationAction
    task_number: str | None
    failure_mode: str | None
    priority: RiskLevel
    reason: str
    suggestion: str


class MaintenanceStrategyProfileBuilderTool:
    def run(self, equipment: Equipment) -> MaintenanceStrategyProfile:
        tasks = [
            MaintenanceStrategyTaskProfile(
                strategy_number=strategy.strategy_number,
                task_number=strategy.task_number,
                task_description=strategy.task_description,
                strategy_type=strategy.strategy_type,
                frequency_value=strategy.frequency_value,
                frequency_unit=strategy.frequency_unit,
                frequency_days=_frequency_days(strategy),
                status=strategy.status,
            )
            for strategy in equipment.maintenance_strategies
        ]

        return MaintenanceStrategyProfile(
            equipment_number=equipment.equipment_number,
            equipment_description=equipment.description,
            equipment_type=equipment.equipment_type,
            criticality=equipment.criticality,
            task_count=len(tasks),
            active_task_count=sum(task.status == "active" for task in tasks),
            strategy_types=sorted(
                {
                    task.strategy_type
                    for task in tasks
                    if task.status == "active"
                }
            ),
            tasks=tasks,
        )


class MaintenanceMixAnalyzerTool:
    def run(self, work_orders: list[WorkOrder]) -> MaintenanceMix:
        corrective = _count_activity(work_orders, {"corrective"})
        emergency = _count_activity(work_orders, {"emergency"})
        preventive = _count_activity(work_orders, {"preventive"})
        inspections = _count_activity(work_orders, {"inspection"})
        condition_monitoring = _count_activity(
            work_orders,
            {"condition_monitoring"},
        )
        planned = preventive + inspections
        reactive = corrective + emergency + condition_monitoring

        return MaintenanceMix(
            total_work_orders=len(work_orders),
            corrective_work_orders=corrective,
            emergency_work_orders=emergency,
            preventive_work_orders=preventive,
            inspection_work_orders=inspections,
            condition_monitoring_work_orders=condition_monitoring,
            corrective_preventive_ratio=_safe_divide(reactive, planned),
            total_cost=_sum_decimal(
                work_order.total_cost for work_order in work_orders
            ),
            total_downtime_hours=_sum_decimal(
                work_order.downtime_hours for work_order in work_orders
            ),
        )


class FailureModeCoverageAnalyzerTool:
    def run(
        self,
        strategies: list[MaintenanceStrategy],
        work_orders: list[WorkOrder],
        repeat_failures: list[RepeatFailureFinding] | None = None,
        repeat_failure_tool: RepeatFailureDetectionTool | None = None,
    ) -> list[FailureModeCoverage]:
        if repeat_failures is None:
            repeat_failures = (
                repeat_failure_tool or RepeatFailureDetectionTool()
            ).run(
                work_orders,
                limit=max(len(work_orders), 1),
            )

        failures = _group_failure_work_orders(work_orders)
        repeat_failures_by_mode = {
            finding.failure_mode: finding for finding in repeat_failures
        }
        active_strategies = [
            strategy for strategy in strategies if strategy.status == "active"
        ]
        findings: list[FailureModeCoverage] = []

        for failure_mode, related_work_orders in failures.items():
            repeat_failure = repeat_failures_by_mode.get(failure_mode)
            matches = [
                strategy
                for strategy in active_strategies
                if _match_score(
                    failure_mode,
                    strategy.task_description,
                )
                > 0
            ]
            best_score = max(
                (
                    _match_score(failure_mode, strategy.task_description)
                    for strategy in matches
                ),
                default=0,
            )
            coverage: CoverageStatus = "uncovered"
            confidence: Literal["low", "medium", "high"] = "high"

            if best_score >= 2:
                coverage = "covered"
                confidence = "high"
            elif best_score == 1:
                coverage = "partial"
                confidence = "medium"

            findings.append(
                FailureModeCoverage(
                    failure_mode=failure_mode,
                    occurrence_count=len(related_work_orders),
                    coverage=coverage,
                    matched_task_numbers=[
                        strategy.task_number
                        for strategy in matches
                        if strategy.task_number
                    ],
                    matched_task_descriptions=[
                        strategy.task_description for strategy in matches
                    ],
                    confidence=confidence,
                    evidence_work_orders=[
                        work_order.order_number
                        for work_order in related_work_orders[:5]
                    ],
                    is_repeat_failure=repeat_failure is not None,
                    repeat_failure_work_order_count=(
                        repeat_failure.work_order_count
                        if repeat_failure is not None
                        else None
                    ),
                    repeat_failure_total_cost=(
                        repeat_failure.total_cost
                        if repeat_failure is not None
                        else None
                    ),
                    repeat_failure_total_downtime_hours=(
                        repeat_failure.total_downtime_hours
                        if repeat_failure is not None
                        else None
                    ),
                    repeat_failure_evidence=(
                        repeat_failure.evidence
                        if repeat_failure is not None
                        else None
                    ),
                )
            )

        return sorted(
            findings,
            key=lambda finding: (
                finding.coverage == "uncovered",
                finding.coverage == "partial",
                finding.is_repeat_failure,
                finding.occurrence_count,
            ),
            reverse=True,
        )


class FrequencyRiskAnalyzerTool:
    def run(
        self,
        strategies: list[MaintenanceStrategy],
        work_orders: list[WorkOrder],
        coverage: list[FailureModeCoverage],
    ) -> list[FrequencyRisk]:
        failure_dates = _failure_dates(work_orders)
        findings: list[FrequencyRisk] = []

        for strategy in strategies:
            if strategy.status != "active":
                continue

            related_modes = [
                finding.failure_mode
                for finding in coverage
                if _match_score(
                    finding.failure_mode,
                    strategy.task_description,
                )
                > 0
            ]
            recurrence_values = [
                recurrence
                for failure_mode in related_modes
                if (
                    recurrence := _shortest_recurrence_days(
                        failure_dates.get(failure_mode, [])
                    )
                )
                is not None
            ]
            recurrence = (
                min(recurrence_values)
                if recurrence_values
                else None
            )
            frequency = _frequency_days(strategy)
            risk: RiskLevel = "unknown"
            reason = "No repeated related failure history is available."

            if frequency is None:
                reason = "Task frequency is missing or uses an unsupported unit."
            elif recurrence is None:
                risk = "low"
                reason = (
                    "No repeated related failure interval is available for "
                    "comparison."
                )
            elif frequency > recurrence:
                risk = "high"
                reason = (
                    f"The task interval is {frequency} days while related "
                    f"failures recur in approximately {recurrence} days."
                )
            elif frequency > recurrence * Decimal("0.75"):
                risk = "medium"
                reason = (
                    "The task interval is close to the observed recurrence "
                    "interval and needs engineering review."
                )
            else:
                risk = "low"
                reason = (
                    "The task interval is shorter than the observed recurrence "
                    "interval, but task effectiveness is not proven."
                )

            findings.append(
                FrequencyRisk(
                    task_number=strategy.task_number,
                    task_description=strategy.task_description,
                    frequency_days=frequency,
                    related_failure_modes=related_modes,
                    observed_recurrence_days=recurrence,
                    risk=risk,
                    reason=reason,
                )
            )

        return findings


class MaintenanceStrategyGapDetectorTool:
    def run(
        self,
        profile: MaintenanceStrategyProfile,
        coverage: list[FailureModeCoverage],
    ) -> list[MaintenanceStrategyGap]:
        gaps: list[MaintenanceStrategyGap] = []

        if profile.active_task_count == 0:
            gaps.append(
                MaintenanceStrategyGap(
                    gap_type="no_active_strategy",
                    failure_mode=None,
                    severity="high",
                    evidence="No active maintenance strategy tasks were found.",
                    recommendation="Create and approve an asset strategy.",
                )
            )

        for finding in coverage:
            if finding.coverage == "uncovered":
                gaps.append(
                    MaintenanceStrategyGap(
                        gap_type="uncovered_failure_mode",
                        failure_mode=finding.failure_mode,
                        severity=_coverage_gap_severity(finding),
                        evidence=_coverage_gap_evidence(finding),
                        recommendation=(
                            "Add or revise a preventive, inspection, or "
                            "condition-monitoring control."
                        ),
                    )
                )
            elif (
                finding.coverage == "partial"
                and finding.occurrence_count >= 2
            ):
                gaps.append(
                    MaintenanceStrategyGap(
                        gap_type="partial_failure_mode_coverage",
                        failure_mode=finding.failure_mode,
                        severity=(
                            "high" if finding.is_repeat_failure else "medium"
                        ),
                        evidence=_partial_coverage_gap_evidence(finding),
                        recommendation=(
                            "Review task method, acceptance limits, and "
                            "follow-up actions."
                        ),
                    )
                )

        return gaps


def _coverage_gap_severity(finding: FailureModeCoverage) -> RiskLevel:
    if finding.is_repeat_failure or finding.occurrence_count >= 2:
        return "high"

    return "medium"


def _coverage_gap_evidence(finding: FailureModeCoverage) -> str:
    evidence = (
        f"{finding.occurrence_count} observed event(s): "
        f"{', '.join(finding.evidence_work_orders)}."
    )
    repeat_evidence = _repeat_failure_evidence(finding)

    if repeat_evidence:
        return f"{evidence} {repeat_evidence}"

    return evidence


def _partial_coverage_gap_evidence(finding: FailureModeCoverage) -> str:
    evidence = (
        "Existing task wording only partially addresses "
        f"{finding.failure_mode}."
    )
    repeat_evidence = _repeat_failure_evidence(finding)

    if repeat_evidence:
        return f"{evidence} {repeat_evidence}"

    return evidence


def _repeat_failure_evidence(finding: FailureModeCoverage) -> str:
    if not finding.is_repeat_failure:
        return ""

    details = [
        (
            f"{finding.repeat_failure_work_order_count} repeat work order(s)"
            if finding.repeat_failure_work_order_count is not None
            else "repeat failure pattern"
        )
    ]

    if finding.repeat_failure_total_downtime_hours is not None:
        details.append(
            f"{finding.repeat_failure_total_downtime_hours} downtime hours"
        )

    if finding.repeat_failure_total_cost is not None:
        details.append(f"{finding.repeat_failure_total_cost} recorded cost")

    evidence = f"Repeat failure context: {', '.join(details)}."

    if finding.repeat_failure_evidence:
        evidence += f" Evidence: {finding.repeat_failure_evidence}."

    return evidence


class MaintenanceStrategyRecommendationBuilderTool:
    def run(
        self,
        profile: MaintenanceStrategyProfile,
        equipment_type: str | None,
        coverage: list[FailureModeCoverage],
        frequency_risks: list[FrequencyRisk],
        gaps: list[MaintenanceStrategyGap],
    ) -> list[MaintenanceStrategyRecommendation]:
        recommendations = [
            MaintenanceStrategyRecommendation(
                action="add",
                task_number=None,
                failure_mode=gap.failure_mode,
                priority=gap.severity,
                reason=gap.evidence,
                suggestion=_gap_recommendation_suggestion(gap),
            )
            for gap in gaps
        ]

        for risk in frequency_risks:
            if risk.risk not in {"high", "medium"}:
                continue

            recommendations.append(
                MaintenanceStrategyRecommendation(
                    action="engineering_review",
                    task_number=risk.task_number,
                    failure_mode=(
                        risk.related_failure_modes[0]
                        if risk.related_failure_modes
                        else None
                    ),
                    priority=risk.risk,
                    reason=risk.reason,
                    suggestion=(
                        "Review the task interval using operating context, "
                        "task execution quality, and site standards."
                    ),
                )
            )

        recurring_covered = [
            finding
            for finding in coverage
            if finding.coverage == "covered"
            and finding.occurrence_count >= 2
        ]
        recommendations.extend(
            [
                MaintenanceStrategyRecommendation(
                    action="modify",
                    task_number=(
                        finding.matched_task_numbers[0]
                        if finding.matched_task_numbers
                        else None
                    ),
                    failure_mode=finding.failure_mode,
                    priority="high",
                    reason=(
                        f"{finding.failure_mode} recurs despite an existing "
                        "related task."
                    ),
                    suggestion=(
                        "Review task method, acceptance criteria, response "
                        "actions, and execution quality."
                    ),
                )
                for finding in recurring_covered
            ]
        )

        existing_failure_modes = {
            recommendation.failure_mode
            for recommendation in recommendations
        }
        for finding in coverage:
            if finding.failure_mode in existing_failure_modes:
                continue

            method = _monitoring_method(equipment_type, finding.failure_mode)
            if method is None:
                continue

            recommendations.append(
                MaintenanceStrategyRecommendation(
                    action="add",
                    task_number=None,
                    failure_mode=finding.failure_mode,
                    priority=_monitoring_priority(finding),
                    reason=_monitoring_reason(finding, method),
                    suggestion=(
                        f"Evaluate {method} and define "
                        "alarm or intervention criteria."
                    ),
                )
            )
            existing_failure_modes.add(finding.failure_mode)

        if not recommendations and profile.active_task_count:
            recommendations.append(
                MaintenanceStrategyRecommendation(
                    action="keep",
                    task_number=None,
                    failure_mode=None,
                    priority="low",
                    reason=(
                        "No material strategy gap was identified from the "
                        "available history."
                    ),
                    suggestion=(
                        "Retain the current tasks and continue monitoring "
                        "failure history."
                    ),
                )
            )

        return recommendations


def _gap_recommendation_suggestion(
    gap: MaintenanceStrategyGap,
) -> str:
    if (
        gap.severity == "high"
        and "Repeat failure context:" in gap.evidence
        and gap.failure_mode is not None
    ):
        return (
            f"Treat {gap.failure_mode} as a high-priority repeat failure gap. "
            f"{gap.recommendation}"
        )

    return gap.recommendation


def _monitoring_priority(finding: FailureModeCoverage) -> RiskLevel:
    if finding.is_repeat_failure or (
        finding.occurrence_count >= 2
        and finding.coverage != "covered"
    ):
        return "high"

    return "medium"


def _monitoring_reason(
    finding: FailureModeCoverage,
    method: str,
) -> str:
    reason = (
        f"{finding.failure_mode} appears in "
        f"{finding.occurrence_count} work order(s); {method} may provide "
        "earlier warning."
    )
    repeat_evidence = _repeat_failure_evidence(finding)

    if repeat_evidence:
        return f"{reason} {repeat_evidence}"

    return reason


def _frequency_days(
    strategy: MaintenanceStrategy,
) -> Decimal | None:
    if strategy.frequency_value is None or strategy.frequency_unit is None:
        return None

    multipliers = {
        "day": Decimal("1"),
        "days": Decimal("1"),
        "week": Decimal("7"),
        "weeks": Decimal("7"),
        "month": Decimal("30.44"),
        "months": Decimal("30.44"),
        "year": Decimal("365.25"),
        "years": Decimal("365.25"),
    }
    multiplier = multipliers.get(strategy.frequency_unit.lower())

    if multiplier is None:
        return None

    return (strategy.frequency_value * multiplier).quantize(
        Decimal("0.01")
    )


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


def _safe_divide(
    numerator: int,
    denominator: int,
) -> Decimal | None:
    if denominator == 0:
        return None

    return (Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal("0.01")
    )


def _group_failure_work_orders(
    work_orders: list[WorkOrder],
) -> dict[str, list[WorkOrder]]:
    grouped: dict[str, list[WorkOrder]] = {}

    for work_order in work_orders:
        if work_order.maintenance_activity_type not in CORRECTIVE_TYPES:
            continue

        for link in work_order.failure_mode_links:
            grouped.setdefault(link.failure_mode.name, []).append(work_order)

    return grouped


def _failure_dates(
    work_orders: list[WorkOrder],
) -> dict[str, list[datetime]]:
    grouped: dict[str, list[datetime]] = {}

    for failure_mode, related_work_orders in _group_failure_work_orders(
        work_orders
    ).items():
        dates = [
            work_order.finished_at or work_order.created_at_source
            for work_order in related_work_orders
            if work_order.finished_at or work_order.created_at_source
        ]
        grouped[failure_mode] = sorted(dates)

    return grouped


def _shortest_recurrence_days(
    dates: list[datetime],
) -> Decimal | None:
    unique_dates = sorted(set(dates))
    if len(unique_dates) < 2:
        return None

    intervals = [
        Decimal(str((current - previous).total_seconds() / 86_400))
        for previous, current in zip(
            unique_dates,
            unique_dates[1:],
            strict=False,
        )
    ]

    return min(intervals).quantize(Decimal("0.01"))


def _tokens(value: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", value.lower())
    return {
        _normalize_token(word)
        for word in words
        if word not in TOKEN_STOP_WORDS
    }


def _normalize_token(token: str) -> str:
    aliases = {
        "mistracking": "tracking",
        "slippage": "slip",
        "leaking": "leak",
        "leakage": "leak",
        "bearings": "bearing",
        "temperatures": "temperature",
    }
    return aliases.get(token, token)


def _match_score(
    failure_mode: str,
    task_description: str,
) -> int:
    return len(_tokens(failure_mode) & _tokens(task_description))


def _monitoring_method(
    equipment_type: str | None,
    failure_mode: str,
) -> str | None:
    text = f"{equipment_type or ''} {failure_mode}".lower()
    methods = (
        ({"bearing", "imbalance", "vibration"}, "vibration and temperature trending"),
        ({"seal", "leak", "packing"}, "leakage inspection or leak detection"),
        ({"temperature", "overheat", "cooling"}, "temperature trending"),
        ({"motor", "current", "insulation"}, "motor current and insulation monitoring"),
        ({"cavitation", "pressure", "capacity"}, "pressure, flow, and vibration trending"),
        ({"belt", "tracking", "slip"}, "belt alignment and vibration monitoring"),
        ({"fouling", "heat exchanger"}, "pressure-drop and temperature-approach trending"),
    )

    for keywords, method in methods:
        if any(keyword in text for keyword in keywords):
            return method

    return None
