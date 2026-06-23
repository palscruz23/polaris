from sqlalchemy.orm import Session

from app.domain.progress import ProgressCallback, report_progress
from app.tools.master_data import EquipmentSearchResult, EquipmentSearchTool


class MasterDataAgent:
    """Read-only specialist for discovering stored equipment master data."""

    def __init__(
        self,
        session: Session,
        equipment_search_tool: EquipmentSearchTool | None = None,
    ):
        self.session = session
        self.equipment_search_tool = (
            equipment_search_tool or EquipmentSearchTool()
        )

    def search_equipment(
        self,
        *,
        query: str | None = None,
        equipment_type: str | None = None,
        functional_location: str | None = None,
        criticality: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
        progress: ProgressCallback | None = None,
    ) -> EquipmentSearchResult:
        report_progress(
            progress,
            stage="tool_started",
            specialist="master_data",
            tool="equipment_search",
            message="Master Data Agent is searching the equipment master.",
        )
        return self.equipment_search_tool.run(
            self.session,
            query=query,
            equipment_type=equipment_type,
            functional_location=functional_location,
            criticality=criticality,
            status=status,
            limit=limit,
            offset=offset,
        )
