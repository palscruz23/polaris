from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.progress import ProgressCallback, report_progress
from app.models import Equipment, WorkOrder, WorkOrderFailureMode
from app.tools.defect_elimination import RepeatFailureDetectionTool
from app.tools.maintenance_strategy import (
    FailureModeCoverage,
    FailureModeCoverageAnalyzerTool,
    FrequencyRisk,
    FrequencyRiskAnalyzerTool,
    MaintenanceMix,
    MaintenanceMixAnalyzerTool,
    MaintenanceStrategyGap,
    MaintenanceStrategyGapDetectorTool,
    MaintenanceStrategyProfile,
    MaintenanceStrategyProfileBuilderTool,
    MaintenanceStrategyRecommendation,
    MaintenanceStrategyRecommendationBuilderTool,
)

MAINTENANCE_STRATEGY_REVIEW_LIMITATIONS = [
    (
        "Task completion and schedule-compliance records are unavailable, so "
        "task effectiveness cannot be established causally."
    ),
    (
        "OEM recommendations, FMEA controls, statutory requirements, labor "
        "hours, and spares usage are not represented in the current dataset."
    ),
    (
        "Frequency findings are engineering-review flags, not approved "
        "interval changes."
    ),
    (
        "No task deletion is recommended without safety, statutory, and "
        "hidden-failure review."
    ),
]


@dataclass(frozen=True)
class AssetMaintenanceStrategyReview:
    profile: MaintenanceStrategyProfile
    maintenance_mix: MaintenanceMix
    failure_mode_coverage: list[FailureModeCoverage]
    frequency_risks: list[FrequencyRisk]
    strategy_gaps: list[MaintenanceStrategyGap]
    recommendations: list[MaintenanceStrategyRecommendation]


@dataclass(frozen=True)
class MaintenanceStrategyReviewFindings:
    reviewed_asset_count: int
    requested_equipment_numbers: list[str]
    missing_equipment_numbers: list[str]
    asset_reviews: list[AssetMaintenanceStrategyReview]
    limitations: list[str]


MaintenanceStrategyIntent = Literal[
    "full_strategy_review",
    "summarize_strategy_profile",
    "maintenance_mix",
    "check_coverage",
    "assess_frequency",
    "detect_gaps",
]


class MaintenanceStrategyAgent:
    """Specialist agent for evidence-based maintenance strategy reviews."""

    def __init__(
        self,
        session: Session,
        profile_tool: MaintenanceStrategyProfileBuilderTool | None = None,
        maintenance_mix_tool: MaintenanceMixAnalyzerTool | None = None,
        repeat_failure_tool: RepeatFailureDetectionTool | None = None,
        coverage_tool: FailureModeCoverageAnalyzerTool | None = None,
        frequency_tool: FrequencyRiskAnalyzerTool | None = None,
        gap_tool: MaintenanceStrategyGapDetectorTool | None = None,
        recommendation_tool: MaintenanceStrategyRecommendationBuilderTool
        | None = None,
    ):
        self.session = session
        self.profile_tool = (
            profile_tool or MaintenanceStrategyProfileBuilderTool()
        )
        self.maintenance_mix_tool = (
            maintenance_mix_tool or MaintenanceMixAnalyzerTool()
        )
        self.repeat_failure_tool = (
            repeat_failure_tool or RepeatFailureDetectionTool()
        )
        self.coverage_tool = (
            coverage_tool or FailureModeCoverageAnalyzerTool()
        )
        self.frequency_tool = frequency_tool or FrequencyRiskAnalyzerTool()
        self.gap_tool = gap_tool or MaintenanceStrategyGapDetectorTool()
        self.recommendation_tool = (
            recommendation_tool
            or MaintenanceStrategyRecommendationBuilderTool()
        )

    def review(
        self,
        equipment_numbers: list[str] | None = None,
        include_failure_history: bool = True,
        maximum_assets: int = 10,
        progress: ProgressCallback | None = None,
    ) -> MaintenanceStrategyReviewFindings:
        return self.analyze(
            intent="full_strategy_review",
            equipment_numbers=equipment_numbers,
            include_failure_history=include_failure_history,
            maximum_assets=maximum_assets,
            progress=progress,
        )

    def analyze(
        self,
        intent: MaintenanceStrategyIntent = "full_strategy_review",
        equipment_numbers: list[str] | None = None,
        include_failure_history: bool = True,
        maximum_assets: int = 10,
        progress: ProgressCallback | None = None,
    ) -> MaintenanceStrategyReviewFindings:
        requested = list(dict.fromkeys(equipment_numbers or []))
        equipment = self._load_equipment(requested)
        equipment_by_number = {
            item.equipment_number: item for item in equipment
        }
        missing = [
            number
            for number in requested
            if number not in equipment_by_number
        ]

        if requested:
            selected = [
                equipment_by_number[number]
                for number in requested
                if number in equipment_by_number
            ][:maximum_assets]
        else:
            selected = sorted(
                equipment,
                key=self._risk_sort_key,
                reverse=True,
            )[:maximum_assets]

        reviews = [
            self._analyze_asset(
                item,
                intent=intent,
                include_failure_history=include_failure_history,
                progress=progress,
            )
            for item in selected
        ]

        return MaintenanceStrategyReviewFindings(
            reviewed_asset_count=len(reviews),
            requested_equipment_numbers=requested,
            missing_equipment_numbers=missing,
            asset_reviews=reviews,
            limitations=MAINTENANCE_STRATEGY_REVIEW_LIMITATIONS,
        )

    def _analyze_asset(
        self,
        equipment: Equipment,
        intent: MaintenanceStrategyIntent,
        include_failure_history: bool,
        progress: ProgressCallback | None,
    ) -> AssetMaintenanceStrategyReview:
        work_orders = (
            list(equipment.work_orders)
            if include_failure_history
            else []
        )
        strategies = list(equipment.maintenance_strategies)
        report_progress(
            progress,
            stage="tool_started",
            specialist="maintenance_strategy",
            tool="maintenance_strategy_profile_builder",
            message=(
                "Maintenance Strategy Agent is building the maintenance "
                "strategy profile "
                f"for {equipment.equipment_number}."
            ),
        )
        profile = self.profile_tool.run(equipment)

        if intent == "summarize_strategy_profile":
            return self._asset_review(profile=profile)

        report_progress(
            progress,
            stage="tool_started",
            specialist="maintenance_strategy",
            tool="maintenance_mix_analyzer",
            message=(
                "Maintenance Strategy Agent is reviewing the preventive and "
                "corrective "
                "maintenance mix."
            ),
        )
        maintenance_mix = self.maintenance_mix_tool.run(work_orders)

        if intent == "maintenance_mix":
            return self._asset_review(
                profile=profile,
                maintenance_mix=maintenance_mix,
            )

        report_progress(
            progress,
            stage="tool_started",
            specialist="maintenance_strategy",
            tool="repeat_failure_detection",
            message=(
                "Maintenance Strategy Agent is checking repeat failures for "
                "coverage context."
            ),
        )
        repeat_failures = self.repeat_failure_tool.run(
            work_orders,
            limit=max(len(work_orders), 1),
        )

        report_progress(
            progress,
            stage="tool_started",
            specialist="maintenance_strategy",
            tool="failure_mode_coverage_analyzer",
            message=(
                "Maintenance Strategy Agent is checking failure-mode coverage."
            ),
        )
        coverage = self.coverage_tool.run(
            strategies,
            work_orders,
            repeat_failures=repeat_failures,
        )

        if intent == "check_coverage":
            return self._asset_review(
                profile=profile,
                maintenance_mix=maintenance_mix,
                failure_mode_coverage=coverage,
            )

        report_progress(
            progress,
            stage="tool_started",
            specialist="maintenance_strategy",
            tool="frequency_risk_analyzer",
            message=(
                "Maintenance Strategy Agent is assessing task-frequency risks."
            ),
        )
        frequency_risks = self.frequency_tool.run(
            strategies,
            work_orders,
            coverage,
        )

        if intent == "assess_frequency":
            return self._asset_review(
                profile=profile,
                maintenance_mix=maintenance_mix,
                failure_mode_coverage=coverage,
                frequency_risks=frequency_risks,
            )

        gaps = self.gap_tool.run(profile, coverage)

        if intent == "detect_gaps":
            return self._asset_review(
                profile=profile,
                maintenance_mix=maintenance_mix,
                failure_mode_coverage=coverage,
                frequency_risks=frequency_risks,
                strategy_gaps=gaps,
            )

        report_progress(
            progress,
            stage="tool_started",
            specialist="maintenance_strategy",
            tool="maintenance_strategy_recommendation_builder",
            message=(
                "Maintenance Strategy Agent is preparing evidence-backed "
                "maintenance strategy "
                "recommendations."
            ),
        )
        recommendations = self.recommendation_tool.run(
            profile=profile,
            equipment_type=equipment.equipment_type,
            coverage=coverage,
            frequency_risks=frequency_risks,
            gaps=gaps,
        )

        return AssetMaintenanceStrategyReview(
            profile=profile,
            maintenance_mix=maintenance_mix,
            failure_mode_coverage=coverage,
            frequency_risks=frequency_risks,
            strategy_gaps=gaps,
            recommendations=recommendations,
        )

    @staticmethod
    def _asset_review(
        *,
        profile: MaintenanceStrategyProfile,
        maintenance_mix: MaintenanceMix | None = None,
        failure_mode_coverage: list[FailureModeCoverage] | None = None,
        frequency_risks: list[FrequencyRisk] | None = None,
        strategy_gaps: list[MaintenanceStrategyGap] | None = None,
        recommendations: list[MaintenanceStrategyRecommendation] | None = None,
    ) -> AssetMaintenanceStrategyReview:
        return AssetMaintenanceStrategyReview(
            profile=profile,
            maintenance_mix=maintenance_mix
            or MaintenanceMix(
                total_work_orders=0,
                corrective_work_orders=0,
                emergency_work_orders=0,
                preventive_work_orders=0,
                inspection_work_orders=0,
                condition_monitoring_work_orders=0,
                corrective_preventive_ratio=None,
                total_cost=Decimal("0"),
                total_downtime_hours=Decimal("0"),
            ),
            failure_mode_coverage=failure_mode_coverage or [],
            frequency_risks=frequency_risks or [],
            strategy_gaps=strategy_gaps or [],
            recommendations=recommendations or [],
        )

    def _load_equipment(
        self,
        equipment_numbers: list[str],
    ) -> list[Equipment]:
        statement = (
            select(Equipment)
            .options(
                selectinload(Equipment.maintenance_strategies),
                selectinload(Equipment.work_orders)
                .selectinload(WorkOrder.failure_mode_links)
                .selectinload(WorkOrderFailureMode.failure_mode),
            )
            .order_by(Equipment.equipment_number)
        )

        if equipment_numbers:
            statement = statement.where(
                Equipment.equipment_number.in_(equipment_numbers)
            )

        return list(self.session.scalars(statement).all())

    @staticmethod
    def _risk_sort_key(
        equipment: Equipment,
    ) -> tuple[int, int, Decimal, Decimal]:
        work_orders = list(equipment.work_orders)
        reactive_count = sum(
            work_order.maintenance_activity_type
            in {"corrective", "emergency", "condition_monitoring"}
            for work_order in work_orders
        )
        criticality_score = {
            "critical": 3,
            "high": 3,
            "medium": 2,
            "low": 1,
        }.get((equipment.criticality or "").lower(), 0)
        downtime = sum(
            (
                work_order.downtime_hours or Decimal("0")
                for work_order in work_orders
            ),
            Decimal("0"),
        )
        cost = sum(
            (
                work_order.total_cost or Decimal("0")
                for work_order in work_orders
            ),
            Decimal("0"),
        )

        return criticality_score, reactive_count, downtime, cost
