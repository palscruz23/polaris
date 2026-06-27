from app.agents.master_data_agent import MasterDataAgent
from app.domain.progress import OrchestrationProgress
from app.tools.master_data import (
    EquipmentRecord,
    EquipmentSearchResult,
    EquipmentSummary,
)


class StubEquipmentSearchTool:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, _session: object, **arguments: object) -> EquipmentSearchResult:
        self.calls.append(arguments)
        return EquipmentSearchResult(
            summary=EquipmentSummary(
                total_matching=1,
                returned_count=1,
                offset=0,
                limit=20,
                has_more=False,
                status_counts={"active": 1},
                equipment_type_counts={"pump": 1},
            ),
            equipment=[
                EquipmentRecord(
                    equipment_number="P-101",
                    description="Process water pump",
                    functional_location="PLANT-A/AREA-1/PUMP-1",
                    equipment_type="pump",
                    system="process_water",
                    criticality="A",
                    status="active",
                    parent_functional_location="PLANT-A/AREA-1",
                )
            ],
        )


def test_master_data_agent_searches_equipment_and_reports_progress() -> None:
    tool = StubEquipmentSearchTool()
    agent = MasterDataAgent(
        session=object(),  # type: ignore[arg-type]
        equipment_search_tool=tool,  # type: ignore[arg-type]
    )
    progress_events: list[OrchestrationProgress] = []

    result = agent.search_equipment(
        query="pump",
        equipment_type="pump",
        progress=progress_events.append,
    )

    assert result.summary.total_matching == 1
    assert result.equipment[0].equipment_number == "P-101"
    assert tool.calls[0]["query"] == "pump"
    assert progress_events == [
        OrchestrationProgress(
            stage="tool_started",
            specialist="master_data",
            tool="equipment_search",
            message="Master Data Agent is searching the equipment master.",
        )
    ]
