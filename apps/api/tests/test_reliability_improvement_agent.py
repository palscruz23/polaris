from datetime import datetime
from decimal import Decimal
from typing import Any

from app.agents.reliability_improvement_agent import (
    ReliabilityImprovementAgent,
)
from app.domain.progress import OrchestrationProgress
from app.models import Equipment, FailureMode, WorkOrder, WorkOrderFailureMode
from app.tools.reliability_improvement import (
    ActionPlanBuilderTool,
    OutcomeReporterTool,
    RoadmapPlannerTool,
    ValueEstimatorTool,
)


class FakeScalarResult:
    def __init__(self, values: list[Any]):
        self.values = values

    def all(self) -> list[Any]:
        return self.values


class FakeSession:
    def __init__(self, work_orders: list[WorkOrder]):
        self.work_orders = work_orders

    def scalars(self, _statement: Any) -> FakeScalarResult:
        return FakeScalarResult(self.work_orders)


def test_reliability_improvement_tools_build_value_plan_outcomes_and_roadmap() -> None:
    work_orders = _improvement_work_orders()

    opportunities = ValueEstimatorTool().run(work_orders, limit=2)
    action_plans = ActionPlanBuilderTool().run(opportunities)
    outcome_reports = OutcomeReporterTool().run(opportunities)
    roadmap = RoadmapPlannerTool().run(opportunities, action_plans)

    assert opportunities[0].equipment_number == "P-101"
    assert opportunities[0].priority == "high"
    assert opportunities[0].opportunity_type == "repeat_failure_elimination"
    assert opportunities[0].estimated_annual_value == Decimal("52000.00")
    assert action_plans[0].owner_role == "Reliability Engineer"
    assert "repeat failure" in action_plans[0].actions[0].lower()
    assert outcome_reports[0].equipment_number == "P-101"
    assert "Downtime hours." in outcome_reports[0].success_measures
    assert roadmap[0].horizon == "now"


def test_reliability_improvement_agent_returns_structured_plan_and_progress() -> None:
    progress_events: list[OrchestrationProgress] = []
    agent = ReliabilityImprovementAgent(
        FakeSession(_improvement_work_orders())  # type: ignore[arg-type]
    )

    findings = agent.build_plan(
        opportunity_limit=2,
        progress=progress_events.append,
    )

    assert findings.opportunities
    assert findings.action_plans
    assert findings.outcome_reports
    assert findings.roadmap
    assert any("Value estimates" in item for item in findings.limitations)
    assert [event.tool for event in progress_events] == [
        "value_estimator",
        "action_plan_builder",
        "outcome_reporter",
        "roadmap_planner",
    ]


def test_reliability_improvement_agent_runs_focused_opportunity_path() -> None:
    progress_events: list[OrchestrationProgress] = []
    agent = ReliabilityImprovementAgent(
        FakeSession(_improvement_work_orders())  # type: ignore[arg-type]
    )

    findings = agent.analyze(
        intent="estimate_opportunities",
        equipment_numbers=["P-101"],
        opportunity_limit=5,
        progress=progress_events.append,
    )

    assert [item.equipment_number for item in findings.opportunities] == [
        "P-101"
    ]
    assert findings.action_plans == []
    assert findings.outcome_reports == []
    assert findings.roadmap == []
    assert [event.tool for event in progress_events] == ["value_estimator"]


def _improvement_work_orders() -> list[WorkOrder]:
    pump = Equipment(
        equipment_number="P-101",
        description="Process water pump",
        equipment_type="pump",
        criticality="high",
    )
    conveyor = Equipment(
        equipment_number="CV-201",
        description="Transfer conveyor",
        equipment_type="conveyor",
        criticality="medium",
    )
    seal_leakage = FailureMode(
        name="Seal leakage",
        equipment_type="pump",
    )
    belt_slip = FailureMode(
        name="Belt slippage",
        equipment_type="conveyor",
    )

    return [
        _work_order(
            pump,
            "WO-101",
            "corrective",
            "2026-01-01",
            Decimal("12000.00"),
            Decimal("15.00"),
            seal_leakage,
        ),
        _work_order(
            pump,
            "WO-102",
            "emergency",
            "2026-02-01",
            Decimal("10000.00"),
            Decimal("15.00"),
            seal_leakage,
        ),
        _work_order(
            conveyor,
            "WO-201",
            "corrective",
            "2026-01-12",
            Decimal("4000.00"),
            Decimal("4.00"),
            belt_slip,
        ),
    ]


def _work_order(
    equipment: Equipment,
    order_number: str,
    activity_type: str,
    finished_at: str,
    total_cost: Decimal,
    downtime: Decimal,
    failure_mode: FailureMode,
) -> WorkOrder:
    work_order = WorkOrder(
        order_number=order_number,
        equipment=equipment,
        maintenance_activity_type=activity_type,
        finished_at=datetime.fromisoformat(finished_at),
        total_cost=total_cost,
        downtime_hours=downtime,
    )
    work_order.failure_mode_links = [
        WorkOrderFailureMode(
            work_order=work_order,
            failure_mode=failure_mode,
            source="import",
            confidence=Decimal("0.900"),
        )
    ]

    return work_order
