from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.agents.defect_elimination_agent import DefectEliminationAgent
from app.models import Equipment, WorkOrder
from app.services.reliability_seed_loader import load_clean_reliability_seed_data
from app.tools.defect_elimination import (
    BadActorAnalysisTool,
    DefectEliminationCharterGeneratorTool,
    FailureInvestigationFinding,
    FiveWhysGeneratorTool,
    MTBFCalculationTool,
    RCAEvidencePlanningTool,
    RCATemplateBuilderTool,
    ReliabilityMetricsTool,
    RepeatFailureDetectionTool,
    WeibullAnalysisTool,
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
    mtbf_metrics = MTBFCalculationTool().run(work_orders, limit=5)
    weibull_analysis = WeibullAnalysisTool().run(work_orders, limit=5)
    evidence_plans = RCAEvidencePlanningTool().run(repeat_failures, limit=2)
    five_whys = FiveWhysGeneratorTool().run(repeat_failures, limit=2)
    rca_templates = RCATemplateBuilderTool().run(repeat_failures, limit=2)
    charters = DefectEliminationCharterGeneratorTool().run(
        repeat_failures=repeat_failures,
        mtbf_metrics=mtbf_metrics,
        evidence_plans=evidence_plans,
        five_whys=five_whys,
        limit=2,
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
    assert len(mtbf_metrics) == 5
    assert mtbf_metrics[0].corrective_event_count >= 2
    assert mtbf_metrics[0].mtbf_days is not None
    assert len(weibull_analysis) == 5
    assert weibull_analysis[0].failure_count >= 3
    assert weibull_analysis[0].shape_beta is not None
    assert weibull_analysis[0].scale_eta_days is not None
    assert weibull_analysis[0].failure_behavior
    assert len(evidence_plans) == 2
    assert evidence_plans[0].evidence_to_collect
    assert len(five_whys) == 2
    assert len(five_whys[0].whys) == 5
    assert len(rca_templates) == 2
    assert "Root cause statement" in rca_templates[0].sections
    assert len(charters) == 2
    assert charters[0].title.startswith("Defect Elimination Charter")
    assert charters[0].problem_statement
    assert charters[0].business_impact
    assert charters[0].required_evidence
    assert charters[0].success_criteria


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
    assert len(findings.mtbf_metrics) == 3
    assert len(findings.weibull_analysis) == 3
    assert len(findings.rca_evidence_plans) == 4
    assert len(findings.five_whys) == 4
    assert len(findings.rca_templates) == 4
    assert len(findings.charters) == 3
    assert findings.recommendations
    assert "defect elimination review" in findings.recommendations[0]
    assert any(
        "MTBF" in recommendation or "Weibull" in recommendation
        for recommendation in findings.recommendations
    )


def test_defect_elimination_agent_runs_focused_mtbf_path_for_specific_equipment() -> None:
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
    session.added.extend(
        [
            _work_order("WO-1", target_asset, "corrective", "2026-01-01", 2),
            _work_order("WO-2", target_asset, "emergency", "2026-01-31", 3),
            _work_order("WO-3", other_asset, "corrective", "2026-01-01", 4),
            _work_order("WO-4", other_asset, "corrective", "2026-04-01", 5),
        ]
    )
    progress_events = []
    agent = DefectEliminationAgent(session)  # type: ignore[arg-type]

    findings = agent.analyze(
        intent="calculate_mtbf",
        equipment_numbers=["PUMP-001"],
        bad_actor_limit=5,
        progress=progress_events.append,
    )

    assert findings.summary.total_work_orders == 2
    assert [finding.equipment_number for finding in findings.mtbf_metrics] == [
        "PUMP-001"
    ]
    assert findings.mtbf_metrics[0].mtbf_days == Decimal("30.00")
    assert findings.bad_actors == []
    assert findings.repeat_failures == []
    assert findings.weibull_analysis == []
    assert findings.rca_evidence_plans == []
    assert [event.tool for event in progress_events] == [
        "reliability_metrics",
        "mtbf_calculation",
    ]


def test_five_whys_generator_supports_specific_failure() -> None:
    analysis = FiveWhysGeneratorTool().run_for_failure(
        equipment_number="PUMP-101",
        equipment_description="Process water pump",
        equipment_type="pump",
        failure_mode="seal leakage",
        evidence="WO-101",
    )

    assert analysis.equipment_number == "PUMP-101"
    assert analysis.failure_mode == "seal leakage"
    assert analysis.problem_statement == (
        "PUMP-101 has a seal leakage failure event requiring RCA. "
        "Evidence: WO-101."
    )
    assert len(analysis.whys) == 5
    assert analysis.whys[0] == "Why did the pump experience seal leakage?"


def test_five_whys_generator_accepts_failure_investigation_findings() -> None:
    failures = [
        FailureInvestigationFinding(
            equipment_number="CONV-201",
            equipment_description="Transfer conveyor",
            equipment_type="conveyor",
            failure_mode="belt tracking issue",
            work_order_count=1,
            evidence="Operator report",
        )
    ]

    analyses = FiveWhysGeneratorTool().run(failures)

    assert len(analyses) == 1
    assert analyses[0].problem_statement == (
        "CONV-201 has a belt tracking issue failure event requiring RCA. "
        "Evidence: Operator report."
    )


def test_rca_template_builder_supports_specific_failure() -> None:
    template = RCATemplateBuilderTool().run_for_failure(
        equipment_number="PUMP-101",
        equipment_description="Process water pump",
        equipment_type="pump",
        failure_mode="seal leakage",
        evidence="WO-101",
    )

    assert template.equipment_number == "PUMP-101"
    assert template.failure_mode == "seal leakage"
    assert template.title == "RCA - PUMP-101 seal leakage"
    assert "Problem statement" in template.sections
    assert (
        "What changed before the pump experienced seal leakage?"
        in template.starter_questions
    )
    assert (
        "Were previous corrective actions completed and verified effective?"
        not in template.starter_questions
    )


def test_rca_template_builder_accepts_failure_investigation_findings() -> None:
    failures = [
        FailureInvestigationFinding(
            equipment_number="CONV-201",
            equipment_description="Transfer conveyor",
            equipment_type="conveyor",
            failure_mode="belt tracking issue",
            work_order_count=1,
            evidence="Operator report",
        )
    ]

    templates = RCATemplateBuilderTool().run(failures)

    assert len(templates) == 1
    assert templates[0].title == "RCA - CONV-201 belt tracking issue"
    assert templates[0].starter_questions[0] == (
        "What changed before the conveyor experienced belt tracking issue?"
    )


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


def _work_order(
    order_number: str,
    equipment: Equipment,
    activity_type: str,
    finished_date: str,
    downtime_hours: int,
) -> WorkOrder:
    return WorkOrder(
        order_number=order_number,
        equipment=equipment,
        maintenance_activity_type=activity_type,
        finished_at=datetime.fromisoformat(finished_date),
        total_cost=Decimal("1000.00"),
        downtime_hours=Decimal(downtime_hours),
    )


def test_weibull_analysis_identifies_wear_out_pattern() -> None:
    asset = Equipment(
        equipment_number="PUMP-004",
        description="Wear out pump",
        equipment_type="pump",
    )
    work_orders = [
        _work_order("WO-W1", asset, "corrective", "2026-01-01", 2),
        _work_order("WO-W2", asset, "corrective", "2026-01-06", 2),
        _work_order("WO-W3", asset, "corrective", "2026-01-16", 2),
        _work_order("WO-W4", asset, "corrective", "2026-02-05", 2),
        _work_order("WO-W5", asset, "corrective", "2026-03-17", 2),
    ]

    finding = WeibullAnalysisTool().run(work_orders, limit=1)[0]

    assert finding.equipment_number == "PUMP-004"
    assert finding.failure_count == 5
    assert finding.interval_count == 4
    assert finding.shape_beta is not None
    assert finding.shape_beta > Decimal("1.10")
    assert finding.scale_eta_days is not None
    assert finding.mean_time_between_failures_days is not None
    assert finding.failure_behavior == "wear-out or age-related pattern"
    assert finding.confidence == "directional"


def test_weibull_analysis_requires_three_failure_intervals() -> None:
    asset = Equipment(
        equipment_number="PUMP-005",
        description="Sparse history pump",
        equipment_type="pump",
    )
    work_orders = [
        _work_order("WO-S1", asset, "corrective", "2026-01-01", 2),
        _work_order("WO-S2", asset, "corrective", "2026-01-06", 2),
        _work_order("WO-S3", asset, "corrective", "2026-01-16", 2),
    ]

    finding = WeibullAnalysisTool().run(work_orders, limit=1)[0]

    assert finding.failure_count == 3
    assert finding.interval_count == 2
    assert finding.shape_beta is None
    assert finding.scale_eta_days is None
    assert finding.failure_behavior == "insufficient interval history"
    assert finding.confidence == "insufficient"
