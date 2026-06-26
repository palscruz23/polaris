from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.agents.defect_elimination_agent import DefectEliminationAgent
from app.models import Equipment, WorkOrder
from app.services.reliability_seed_loader import load_clean_reliability_seed_data
from app.tools.defect_elimination import (
    BadActorAnalysisTool,
    FailureModeBadActorAnalysisTool,
    ReliabilityMetricsTool,
    RepeatFailureDetectionTool,
)


class FakeScalarResult:
    def __init__(self, values: list[Any]):
        self.values = values

    def all(self) -> list[Any]:
        return self.values


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commit_count = 0

    def add(self, item: Any) -> None:
        self.added.append(item)

    def scalar(self, _statement: Any) -> None:
        return None

    def scalars(self, _statement: Any) -> FakeScalarResult:
        return FakeScalarResult(
            [
                item
                for item in self.added
                if isinstance(item, WorkOrder)
            ]
        )

    def commit(self) -> None:
        self.commit_count += 1


def test_defect_elimination_tools_analyze_seeded_work_orders() -> None:
    session = _load_seed_data()
    work_orders = _work_orders(session)

    summary = ReliabilityMetricsTool().summarize(work_orders)
    bad_actors = BadActorAnalysisTool().run(work_orders, limit=5)
    repeat_failures = RepeatFailureDetectionTool().run(work_orders, limit=5)
    failure_mode_bad_actors = FailureModeBadActorAnalysisTool().run(
        repeat_failures,
        limit=5,
    )

    assert summary.total_work_orders == 1000
    assert summary.corrective_work_orders > 0
    assert summary.emergency_work_orders > 0
    assert summary.preventive_work_orders > 0
    assert summary.corrective_preventive_ratio is not None
    assert len(bad_actors) == 5
    assert bad_actors[0].corrective_work_orders > 0
    assert bad_actors[0].total_downtime_hours > 0
    assert bad_actors[0].corrective_event_count >= 2
    assert bad_actors[0].mtbf_days is not None
    assert len(repeat_failures) == 5
    assert repeat_failures[0].work_order_count >= 2
    assert repeat_failures[0].evidence.startswith("WO-")
    assert len(failure_mode_bad_actors) == 5
    assert failure_mode_bad_actors[0].repeat_work_order_count >= 2
    assert failure_mode_bad_actors[0].failure_mode


def test_defect_elimination_agent_returns_structured_findings() -> None:
    session = _load_seed_data()
    agent = DefectEliminationAgent(session)

    findings = agent.build_overview(
        bad_actor_limit=3,
        repeat_failure_limit=4,
        minimum_repeat_occurrences=3,
    )

    assert findings.summary.total_work_orders == 1000
    assert len(findings.bad_actors) == 3
    assert len(findings.repeat_failures) == 4
    assert len(findings.failure_mode_bad_actors) == 3
    assert findings.recommendations
    assert "defect elimination review" in findings.recommendations[0]
    assert any(
        "recurring failure mode" in recommendation
        for recommendation in findings.recommendations
    )


def test_defect_elimination_agent_runs_focused_failure_mode_bad_actor_path() -> None:
    target_asset = Equipment(
        equipment_number="PUMP-001",
        description="Target pump",
        equipment_type="pump",
    )
    other_asset = Equipment(
        equipment_number="PUMP-002",
        description="Other pump",
        equipment_type="pump",
    )
    session = FakeSession()
    seal_leak = _failure_mode("Seal leak")
    bearing_failure = _failure_mode("Bearing failure")
    session.added.extend(
        [
            _work_order(
                "WO-1",
                target_asset,
                "corrective",
                "2026-01-01",
                2,
                seal_leak,
            ),
            _work_order(
                "WO-2",
                target_asset,
                "emergency",
                "2026-01-31",
                3,
                seal_leak,
            ),
            _work_order(
                "WO-3",
                other_asset,
                "corrective",
                "2026-01-01",
                4,
                bearing_failure,
            ),
            _work_order(
                "WO-4",
                other_asset,
                "corrective",
                "2026-04-01",
                5,
                bearing_failure,
            ),
            _work_order(
                "WO-5",
                other_asset,
                "corrective",
                "2026-05-01",
                6,
                bearing_failure,
            ),
        ]
    )
    progress_events = []
    agent = DefectEliminationAgent(session)  # type: ignore[arg-type]

    findings = agent.analyze(
        intent="rank_failure_mode_bad_actors",
        equipment_numbers=["PUMP-001"],
        bad_actor_limit=5,
        progress=progress_events.append,
    )

    assert findings.summary.total_work_orders == 2
    assert [
        finding.equipment_number
        for finding in findings.failure_mode_bad_actors
    ] == ["PUMP-001"]
    assert findings.failure_mode_bad_actors[0].failure_mode == "Seal leak"
    assert findings.failure_mode_bad_actors[0].repeat_work_order_count == 2
    assert findings.bad_actors == []
    assert findings.repeat_failures
    assert [event.tool for event in progress_events] == [
        "reliability_metrics",
        "repeat_failure_detection",
        "failure_mode_bad_actor_analysis",
    ]


def test_bad_actor_analysis_ranks_shortest_mtbf_first() -> None:
    high_frequency_asset = Equipment(
        equipment_number="PUMP-001",
        description="High frequency pump",
        equipment_type="pump",
    )
    lower_frequency_asset = Equipment(
        equipment_number="PUMP-002",
        description="Lower frequency pump",
        equipment_type="pump",
    )
    single_event_asset = Equipment(
        equipment_number="PUMP-003",
        description="Single event pump",
        equipment_type="pump",
    )
    work_orders = [
        _work_order("WO-1", high_frequency_asset, "corrective", "2026-01-01", 2),
        _work_order("WO-2", high_frequency_asset, "corrective", "2026-01-11", 3),
        _work_order("WO-3", lower_frequency_asset, "corrective", "2026-01-01", 20),
        _work_order("WO-4", lower_frequency_asset, "corrective", "2026-04-01", 30),
        _work_order("WO-5", single_event_asset, "emergency", "2026-01-01", 100),
    ]

    bad_actors = BadActorAnalysisTool().run(work_orders, limit=3)

    assert [finding.equipment_number for finding in bad_actors] == [
        "PUMP-001",
        "PUMP-002",
        "PUMP-003",
    ]
    assert bad_actors[0].mtbf_days == Decimal("10.00")
    assert bad_actors[1].mtbf_days == Decimal("90.00")
    assert bad_actors[2].mtbf_days is None


def _load_seed_data() -> FakeSession:
    session = FakeSession()
    load_clean_reliability_seed_data(
        session,
        Path("sample_data/reliability"),
    )

    return session


def _work_orders(session: FakeSession) -> list[WorkOrder]:
    return [
        item
        for item in session.added
        if isinstance(item, WorkOrder)
    ]


def _failure_mode(name: str):
    from app.models import FailureMode

    return FailureMode(name=name)


def _work_order(
    order_number: str,
    equipment: Equipment,
    activity_type: str,
    finished_date: str,
    downtime_hours: int,
    failure_mode=None,
) -> WorkOrder:
    work_order = WorkOrder(
        order_number=order_number,
        equipment=equipment,
        maintenance_activity_type=activity_type,
        finished_at=datetime.fromisoformat(finished_date),
        total_cost=Decimal("1000.00"),
        downtime_hours=Decimal(downtime_hours),
    )
    if failure_mode is not None:
        from app.models import WorkOrderFailureMode

        work_order.failure_mode_links = [
            WorkOrderFailureMode(failure_mode=failure_mode, source="test")
        ]

    return work_order
