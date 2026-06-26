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
from app.tools.defect_elimination import RepeatFailureFinding
from app.tools.maintenance_strategy import (
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


class FakeRepeatFailureTool:
    def __init__(self, findings: list[RepeatFailureFinding]):
        self.findings = findings
        self.call_count = 0

    def run(
        self,
        _work_orders: list[WorkOrder],
        _minimum_occurrences: int = 2,
        limit: int = 10,
    ) -> list[RepeatFailureFinding]:
        self.call_count += 1
        return self.findings[:limit]


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
    recommendations = MaintenanceStrategyRecommendationBuilderTool().run(
        profile,
        equipment.equipment_type,
        coverage,
        frequency_risks,
        gaps,
    )

    coverage_by_mode = {
        finding.failure_mode: finding for finding in coverage
    }
    frequency_by_task = {
        finding.task_number: finding for finding in frequency_risks
    }

    assert profile.task_count == 2
    assert profile.strategy_types == ["condition_based", "inspection"]
    assert mix.corrective_work_orders == 3
    assert mix.emergency_work_orders == 1
    assert mix.preventive_work_orders == 1
    assert mix.corrective_preventive_ratio == Decimal("4.00")
    assert coverage_by_mode["Seal leakage"].coverage == "covered"
    assert coverage_by_mode["Seal leakage"].occurrence_count == 2
    assert coverage_by_mode["Seal leakage"].is_repeat_failure is True
    assert coverage_by_mode["Seal leakage"].repeat_failure_work_order_count == 2
    assert coverage_by_mode["Cavitation"].coverage == "uncovered"
    assert coverage_by_mode["Cavitation"].is_repeat_failure is False
    assert frequency_by_task["P-101-TASK-02"].risk == "high"
    assert any(
        gap.failure_mode == "Cavitation"
        and gap.gap_type == "uncovered_failure_mode"
        for gap in gaps
    )
    assert any(
        recommendation.action == "modify"
        and recommendation.failure_mode == "Seal leakage"
        for recommendation in recommendations
    )
    assert any(
        recommendation.action == "add"
        and recommendation.failure_mode == "Cavitation"
        and "condition-monitoring control" in recommendation.suggestion
        for recommendation in recommendations
    )
    assert any(
        recommendation.action == "add"
        and recommendation.failure_mode == "Vibration imbalance"
        and "vibration and temperature trending" in recommendation.suggestion
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


def test_maintenance_strategy_agent_reuses_repeat_failure_findings_for_coverage() -> None:
    equipment = _pump_with_maintenance_strategy_history()
    repeat_tool = FakeRepeatFailureTool(
        [
            RepeatFailureFinding(
                equipment_number="P-101",
                equipment_description="Process water pump",
                failure_mode="Cavitation",
                equipment_type="pump",
                work_order_count=7,
                total_cost=Decimal("9000"),
                total_downtime_hours=Decimal("42"),
                first_seen_at=datetime.fromisoformat("2026-01-15"),
                last_seen_at=datetime.fromisoformat("2026-03-15"),
                evidence="WO-3, WO-9",
            )
        ]
    )
    agent = MaintenanceStrategyAgent(
        FakeSession([equipment]),  # type: ignore[arg-type]
        repeat_failure_tool=repeat_tool,  # type: ignore[arg-type]
    )

    findings = agent.analyze(
        intent="check_coverage",
        equipment_numbers=["P-101"],
        maximum_assets=1,
    )
    coverage_by_mode = {
        finding.failure_mode: finding
        for finding in findings.asset_reviews[0].failure_mode_coverage
    }

    assert repeat_tool.call_count == 1
    assert coverage_by_mode["Cavitation"].is_repeat_failure is True
    assert coverage_by_mode["Cavitation"].repeat_failure_work_order_count == 7
    assert coverage_by_mode["Cavitation"].repeat_failure_total_cost == Decimal(
        "9000"
    )
    assert coverage_by_mode["Cavitation"].repeat_failure_evidence == "WO-3, WO-9"


def test_maintenance_strategy_gap_detector_prioritizes_repeat_failures() -> None:
    equipment = _pump_with_maintenance_strategy_history()
    repeat_tool = FakeRepeatFailureTool(
        [
            RepeatFailureFinding(
                equipment_number="P-101",
                equipment_description="Process water pump",
                failure_mode="Cavitation",
                equipment_type="pump",
                work_order_count=7,
                total_cost=Decimal("9000"),
                total_downtime_hours=Decimal("42"),
                first_seen_at=datetime.fromisoformat("2026-01-15"),
                last_seen_at=datetime.fromisoformat("2026-03-15"),
                evidence="WO-3, WO-9",
            )
        ]
    )
    agent = MaintenanceStrategyAgent(
        FakeSession([equipment]),  # type: ignore[arg-type]
        repeat_failure_tool=repeat_tool,  # type: ignore[arg-type]
    )

    findings = agent.analyze(
        intent="detect_gaps",
        equipment_numbers=["P-101"],
        maximum_assets=1,
    )
    gap_by_mode = {
        gap.failure_mode: gap
        for gap in findings.asset_reviews[0].strategy_gaps
    }

    assert gap_by_mode["Cavitation"].severity == "high"
    assert "7 repeat work order(s)" in gap_by_mode["Cavitation"].evidence
    assert "42 downtime hours" in gap_by_mode["Cavitation"].evidence
    assert "9000 recorded cost" in gap_by_mode["Cavitation"].evidence
    assert "WO-3, WO-9" in gap_by_mode["Cavitation"].evidence


def test_maintenance_strategy_recommendations_explain_repeat_failure_priority() -> None:
    equipment = _pump_with_maintenance_strategy_history()
    repeat_tool = FakeRepeatFailureTool(
        [
            RepeatFailureFinding(
                equipment_number="P-101",
                equipment_description="Process water pump",
                failure_mode="Cavitation",
                equipment_type="pump",
                work_order_count=7,
                total_cost=Decimal("9000"),
                total_downtime_hours=Decimal("42"),
                first_seen_at=datetime.fromisoformat("2026-01-15"),
                last_seen_at=datetime.fromisoformat("2026-03-15"),
                evidence="WO-3, WO-9",
            )
        ]
    )
    agent = MaintenanceStrategyAgent(
        FakeSession([equipment]),  # type: ignore[arg-type]
        repeat_failure_tool=repeat_tool,  # type: ignore[arg-type]
    )

    findings = agent.review(
        equipment_numbers=["P-101"],
        maximum_assets=1,
    )
    recommendation_by_mode = {
        recommendation.failure_mode: recommendation
        for recommendation in findings.asset_reviews[0].recommendations
        if recommendation.action == "add"
    }

    assert recommendation_by_mode["Cavitation"].priority == "high"
    assert (
        "Repeat failure context"
        in recommendation_by_mode["Cavitation"].reason
    )
    assert (
        "high-priority repeat failure gap"
        in recommendation_by_mode["Cavitation"].suggestion
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
        "repeat_failure_detection",
        "failure_mode_coverage_analyzer",
        "frequency_risk_analyzer",
        "maintenance_strategy_recommendation_builder",
    ]
    assert progress_events[3].message == (
        "Maintenance Strategy Agent is checking failure-mode coverage."
    )


def test_maintenance_strategy_agent_runs_focused_gap_path() -> None:
    equipment = _pump_with_maintenance_strategy_history()
    agent = MaintenanceStrategyAgent(FakeSession([equipment]))  # type: ignore[arg-type]
    progress_events: list[OrchestrationProgress] = []

    findings = agent.analyze(
        intent="detect_gaps",
        equipment_numbers=["P-101"],
        maximum_assets=1,
        progress=progress_events.append,
    )
    review = findings.asset_reviews[0]

    assert review.strategy_gaps
    assert any(gap.failure_mode == "Cavitation" for gap in review.strategy_gaps)
    assert review.recommendations == []
    assert [event.tool for event in progress_events] == [
        "maintenance_strategy_profile_builder",
        "maintenance_mix_analyzer",
        "repeat_failure_detection",
        "failure_mode_coverage_analyzer",
        "frequency_risk_analyzer",
    ]


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
    vibration_imbalance = FailureMode(
        name="Vibration imbalance",
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
        _work_order(
            equipment,
            "WO-5",
            "corrective",
            "2026-01-25",
            vibration_imbalance,
            downtime=2,
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
