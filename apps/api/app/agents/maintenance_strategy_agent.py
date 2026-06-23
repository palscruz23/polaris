from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.progress import ProgressCallback, report_progress
from app.models import Equipment, WorkOrder, WorkOrderFailureMode
from app.tools.maintenance_strategy import (
    ConditionMonitoringOpportunity,
    ConditionMonitoringOpportunityAnalyzerTool,
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
    condition_monitoring_opportunities: list[
        ConditionMonitoringOpportunity
    ]
    recommendations: list[MaintenanceStrategyRecommendation]


@dataclass(frozen=True)
class MaintenanceStrategyReviewFindings:
    reviewed_asset_count: int
    requested_equipment_numbers: list[str]
    missing_equipment_numbers: list[str]
    asset_reviews: list[AssetMaintenanceStrategyReview]
    limitations: list[str]


class MaintenanceStrategyAgent:
    """Specialist agent for evidence-based maintenance strategy reviews."""

    def __init__(
        self,
        session: Session,
        profile_tool: MaintenanceStrategyProfileBuilderTool | None = None,
        maintenance_mix_tool: MaintenanceMixAnalyzerTool | None = None,
        coverage_tool: FailureModeCoverageAnalyzerTool | None = None,
        frequency_tool: FrequencyRiskAnalyzerTool | None = None,
        gap_tool: MaintenanceStrategyGapDetectorTool | None = None,
        monitoring_tool: ConditionMonitoringOpportunityAnalyzerTool
        | None = None,
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
        self.coverage_tool = (
            coverage_tool or FailureModeCoverageAnalyzerTool()
        )
        self.frequency_tool = frequency_tool or FrequencyRiskAnalyzerTool()
        self.gap_tool = gap_tool or MaintenanceStrategyGapDetectorTool()
        self.monitoring_tool = (
            monitoring_tool or ConditionMonitoringOpportunityAnalyzerTool()
        )
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
            self._review_asset(
                item,
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

    def _review_asset(
        self,
        equipment: Equipment,
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
        report_progress(
            progress,
            stage="tool_started",
            specialist="maintenance_strategy",
            tool="failure_mode_coverage_analyzer",
            message=(
                "Maintenance Strategy Agent is checking failure-mode coverage."
            ),
        )
        coverage = self.coverage_tool.run(strategies, work_orders)
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
        gaps = self.gap_tool.run(profile, coverage)
        opportunities = self.monitoring_tool.run(
            equipment.equipment_type,
            coverage,
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
            coverage=coverage,
            frequency_risks=frequency_risks,
            gaps=gaps,
            opportunities=opportunities,
        )

        return AssetMaintenanceStrategyReview(
            profile=profile,
            maintenance_mix=maintenance_mix,
            failure_mode_coverage=coverage,
            frequency_risks=frequency_risks,
            strategy_gaps=gaps,
            condition_monitoring_opportunities=opportunities,
            recommendations=recommendations,
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
