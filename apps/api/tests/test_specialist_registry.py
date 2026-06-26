from app.agents.registry import (
    DefectEliminationArguments,
    EquipmentSearchArguments,
    MaintenanceStrategyReviewArguments,
    SpecialistRegistry,
)
from app.domain.orchestration import (
    AgentToolCall,
    AgentToolDefinition,
)
from app.domain.progress import ProgressCallback


class StubSpecialist:
    @property
    def definition(self) -> AgentToolDefinition:
        return AgentToolDefinition(
            name="stub_analysis",
            description="Return a test finding.",
            input_schema={"type": "object", "properties": {}},
        )

    def execute(
        self,
        arguments: dict[str, object],
        progress: ProgressCallback | None = None,
    ) -> str:
        del progress
        return f'{{"arguments":{arguments!r}}}'


def test_registry_exposes_and_executes_registered_specialist() -> None:
    registry = SpecialistRegistry(
        session=None,  # type: ignore[arg-type]
        specialists=(StubSpecialist(),),
    )
    call = AgentToolCall(
        id="call-1",
        name="stub_analysis",
        arguments={"asset": "P-101"},
    )

    result = registry.execute(call)

    assert registry.definitions[0].name == "stub_analysis"
    assert result.call_id == "call-1"
    assert result.tool_name == "stub_analysis"
    assert "P-101" in result.content
    assert result.is_error is False


def test_registry_returns_structured_error_for_unknown_specialist() -> None:
    registry = SpecialistRegistry(
        session=None,  # type: ignore[arg-type]
        specialists=(StubSpecialist(),),
    )

    result = registry.execute(
        AgentToolCall(
            id="call-unknown",
            name="missing_analysis",
            arguments={},
        )
    )

    assert result.is_error is True
    assert result.call_id == "call-unknown"
    assert "Unknown specialist capability" in result.content


def test_defect_elimination_arguments_enforce_bounded_limits() -> None:
    schema = DefectEliminationArguments.model_json_schema()

    assert schema["properties"]["bad_actor_limit"]["maximum"] == 10
    assert schema["properties"]["repeat_failure_limit"]["maximum"] == 10
    assert schema["properties"]["equipment_numbers"]["maxItems"] == 10
    assert set(schema["properties"]["intent"]["enum"]) == {
        "overview",
        "rank_bad_actors",
        "find_repeat_failures",
        "rank_failure_mode_bad_actors",
    }


def test_default_registry_exposes_all_specialist_capabilities() -> None:
    registry = SpecialistRegistry(session=None)  # type: ignore[arg-type]

    assert [definition.name for definition in registry.definitions] == [
        "search_equipment_master",
        "analyze_defect_elimination",
        "review_maintenance_strategy",
    ]


def test_equipment_search_arguments_enforce_pagination_limits() -> None:
    schema = EquipmentSearchArguments.model_json_schema()
    query_options = schema["properties"]["query"]["anyOf"]

    assert query_options[0]["maxLength"] == 100
    assert schema["properties"]["limit"]["maximum"] == 50
    assert schema["properties"]["offset"]["minimum"] == 0


def test_maintenance_strategy_arguments_enforce_asset_limits() -> None:
    schema = MaintenanceStrategyReviewArguments.model_json_schema()

    assert schema["properties"]["equipment_numbers"]["maxItems"] == 10
    assert schema["properties"]["maximum_assets"]["maximum"] == 10
    assert set(schema["properties"]["intent"]["enum"]) == {
        "full_strategy_review",
        "summarize_strategy_profile",
        "maintenance_mix",
        "check_coverage",
        "assess_frequency",
        "detect_gaps",
    }
