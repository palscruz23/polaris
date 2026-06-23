import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.agents.registry import MaintenanceStrategySpecialist
from app.agents.maintenance_strategy_agent import MaintenanceStrategyAgent
from app.domain.progress import OrchestrationProgress
from app.models import (
    Equipment,
    FailureMode,
    MaintenanceStrategy,
    WorkOrder,
    WorkOrderFailureMode,
)
from app.tools.maintenance_strategy import (
    ConditionMonitoringOpportunityAnalyzerTool,
    FailureModeCoverageAnalyzerTool,
    FrequencyRiskAnalyzerTool,
    MaintenanceMixAnalyzerTool,
    MaintenanceStrategyGapDetectorTool,
    MaintenanceStrategyProfileBuilderTool,
    MaintenanceStrategyRecommendationBuilderTool,
)


class FakeScalarResult:
    def __init__(self, values: list[Any]):
        self.values = values

    def all(self) -> list[Any]:
        return self.values


class FakeSession:
    def __init__(self, equipment: list[Equipment]):
        self.equipment = equipment

    def scalars(self, _statement: Any) -> FakeScalarResult:
        return FakeScalarResult(self.equipment)


def test_maintenance_strategy_tools_find_covered_recurring_and_uncovered_failures() -> None:
    equipment = _pump_with_maintenance_strategy_history()
    strategies = list(equipment.maintenance_strategies)
    work_orders = list(equipment.work_orders)

    profile = MaintenanceStrategyProfileBuilderTool().run(equipment)
    mix = MaintenanceMixAnalyzerTool().run(work_orders)
    coverage = FailureModeCoverageAnalyzerTool().run(
        strategies,
        work_orders,
    )
    frequency_risks = FrequencyRiskAnalyzerTool().run(
        strategies,
        work_orders,
        coverage,
    )
    gaps = MaintenanceStrategyGapDetectorTool().run(profile, coverage)
    opportunities = ConditionMonitoringOpportunityAnalyzerTool().run(
        equipment.equipment_type,
        coverage,
    )
    recommendations = MaintenanceStrategyRecommendationBuilderTool().run(
        profile,
        coverage,
        frequency_risks,
        gaps,
        opportunities,
    )

    coverage_by_mode = {
        finding.failure_mode: finding for finding in coverage
    }
    frequency_by_task = {
        finding.task_number: finding for finding in frequency_risks
    }

    assert profile.task_count == 2
    assert profile.strategy_types == ["condition_based", "inspection"]
    assert mix.corrective_work_orders == 2
    assert mix.emergency_work_orders == 1
    assert mix.preventive_work_orders == 1
    assert mix.corrective_preventive_ratio == Decimal("3.00")
    assert coverage_by_mode["Seal leakage"].coverage == "covered"
    assert coverage_by_mode["Seal leakage"].occurrence_count == 2
    assert coverage_by_mode["Cavitation"].coverage == "uncovered"
    assert frequency_by_task["P-101-TASK-02"].risk == "high"
    assert any(
        gap.failure_mode == "Cavitation"
        and gap.gap_type == "uncovered_failure_mode"
        for gap in gaps
    )
    assert any(
        opportunity.failure_mode == "Cavitation"
        and "pressure" in opportunity.monitoring_method
        for opportunity in opportunities
    )
    assert any(
        recommendation.action == "modify"
        and recommendation.failure_mode == "Seal leakage"
        for recommendation in recommendations
    )
    assert any(
        recommendation.action == "add"
        and recommendation.failure_mode == "Cavitation"
        for recommendation in recommendations
    )


def test_maintenance_strategy_agent_returns_structured_asset_review_and_limit() -> None:
    equipment = _pump_with_maintenance_strategy_history()
    agent = MaintenanceStrategyAgent(FakeSession([equipment]))  # type: ignore[arg-type]

    findings = agent.review(
        equipment_numbers=["P-101", "MISSING-1"],
        maximum_assets=1,
    )

    assert findings.reviewed_asset_count == 1
    assert findings.missing_equipment_numbers == ["MISSING-1"]
    assert findings.asset_reviews[0].profile.equipment_number == "P-101"
    assert findings.asset_reviews[0].recommendations
    assert any("Task completion" in item for item in findings.limitations)
    assert all(
        recommendation.action != "delete"
        for recommendation in findings.asset_reviews[0].recommendations
    )


def test_maintenance_strategy_agent_reports_named_tool_progress() -> None:
    equipment = _pump_with_maintenance_strategy_history()
    agent = MaintenanceStrategyAgent(FakeSession([equipment]))  # type: ignore[arg-type]
    progress_events: list[OrchestrationProgress] = []

    agent.review(
        equipment_numbers=["P-101"],
        maximum_assets=1,
        progress=progress_events.append,
    )

    assert [event.tool for event in progress_events] == [
        "maintenance_strategy_profile_builder",
        "maintenance_mix_analyzer",
        "failure_mode_coverage_analyzer",
        "frequency_risk_analyzer",
        "maintenance_strategy_recommendation_builder",
    ]
    assert progress_events[2].message == (
        "Maintenance Strategy Agent is checking failure-mode coverage."
    )


def test_maintenance_strategy_specialist_returns_json_for_orchestration() -> None:
    equipment = _pump_with_maintenance_strategy_history()
    specialist = MaintenanceStrategySpecialist(
        FakeSession([equipment])  # type: ignore[arg-type]
    )

    result = json.loads(
        specialist.execute(
            {
                "equipment_numbers": ["P-101"],
                "maximum_assets": 1,
            }
        )
    )

    assert result["reviewed_asset_count"] == 1
    assert result["asset_reviews"][0]["profile"]["equipment_number"] == "P-101"
    assert result["asset_reviews"][0]["recommendations"]


def _pump_with_maintenance_strategy_history() -> Equipment:
    equipment = Equipment(
        equipment_number="P-101",
        description="Process water pump",
        equipment_type="pump",
        criticality="high",
        status="active",
    )
    equipment.maintenance_strategies = [
        MaintenanceStrategy(
            strategy_number="PM-PUMP-P-101",
            task_number="P-101-TASK-01",
            task_description="Inspect vibration and bearing temperature",
            strategy_type="inspection",
            frequency_value=Decimal("4"),
            frequency_unit="weeks",
            status="active",
        ),
        MaintenanceStrategy(
            strategy_number="PM-PUMP-P-101",
            task_number="P-101-TASK-02",
            task_description="Inspect mechanical seal leakage",
            strategy_type="condition_based",
            frequency_value=Decimal("4"),
            frequency_unit="weeks",
            status="active",
        ),
    ]

    seal_leakage = FailureMode(
        name="Seal leakage",
        equipment_type="pump",
    )
    cavitation = FailureMode(
        name="Cavitation",
        equipment_type="pump",
    )
    equipment.work_orders = [
        _work_order(
            equipment,
            "WO-1",
            "corrective",
            "2026-01-01",
            seal_leakage,
            downtime=5,
        ),
        _work_order(
            equipment,
            "WO-2",
            "corrective",
            "2026-01-11",
            seal_leakage,
            downtime=7,
        ),
        _work_order(
            equipment,
            "WO-3",
            "emergency",
            "2026-01-15",
            cavitation,
            downtime=10,
        ),
        _work_order(
            equipment,
            "WO-4",
            "preventive",
            "2026-01-20",
            None,
            downtime=0,
        ),
    ]

    return equipment


def _work_order(
    equipment: Equipment,
    order_number: str,
    activity_type: str,
    finished_at: str,
    failure_mode: FailureMode | None,
    downtime: int,
) -> WorkOrder:
    work_order = WorkOrder(
        order_number=order_number,
        equipment=equipment,
        maintenance_activity_type=activity_type,
        finished_at=datetime.fromisoformat(finished_at),
        total_cost=Decimal("1000"),
        downtime_hours=Decimal(downtime),
    )

    if failure_mode is not None:
        work_order.failure_mode_links = [
            WorkOrderFailureMode(
                failure_mode=failure_mode,
                source="import",
            )
        ]

    return work_order
