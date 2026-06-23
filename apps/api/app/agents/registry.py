from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.agents.defect_elimination_agent import DefectEliminationAgent
from app.agents.master_data_agent import MasterDataAgent
from app.agents.maintenance_strategy_agent import MaintenanceStrategyAgent
from app.domain.orchestration import (
    AgentToolCall,
    AgentToolDefinition,
    AgentToolResult,
)
from app.domain.progress import ProgressCallback
from app.schemas.defect_elimination import DefectEliminationOverviewResponse
from app.schemas.master_data import EquipmentSearchResponse
from app.schemas.maintenance_strategy import MaintenanceStrategyReviewResponse


class Specialist(Protocol):
    @property
    def definition(self) -> AgentToolDefinition:
        """Describe the specialist capability exposed to the orchestrator."""

    def execute(
        self,
        arguments: dict[str, object],
        progress: ProgressCallback | None = None,
    ) -> str:
        """Execute the specialist and return structured JSON findings."""


class DefectEliminationArguments(BaseModel):
    bad_actor_limit: int = Field(default=5, ge=1, le=10)
    repeat_failure_limit: int = Field(default=5, ge=1, le=10)
    minimum_repeat_occurrences: int = Field(default=2, ge=2, le=20)


class DefectEliminationSpecialist:
    def __init__(self, session: Session):
        self.agent = DefectEliminationAgent(session)

    @property
    def definition(self) -> AgentToolDefinition:
        return AgentToolDefinition(
            name="analyze_defect_elimination",
            description=(
                "Analyze stored work-order data for bad actors, repeat "
                "failures, MTBF patterns, RCA preparation, defect elimination "
                "charters, and prioritized recommendations. Use this when the "
                "user asks about actual equipment or failure history in the "
                "reliability dataset."
            ),
            input_schema=DefectEliminationArguments.model_json_schema(),
        )

    def execute(
        self,
        arguments: dict[str, object],
        progress: ProgressCallback | None = None,
    ) -> str:
        request = DefectEliminationArguments.model_validate(arguments)
        findings = self.agent.build_overview(
            bad_actor_limit=request.bad_actor_limit,
            repeat_failure_limit=request.repeat_failure_limit,
            minimum_repeat_occurrences=request.minimum_repeat_occurrences,
            progress=progress,
        )
        response = DefectEliminationOverviewResponse.model_validate(
            findings,
            from_attributes=True,
        )

        return response.model_dump_json()


class EquipmentSearchArguments(BaseModel):
    query: str | None = Field(default=None, max_length=100)
    equipment_type: str | None = Field(default=None, max_length=100)
    functional_location: str | None = Field(default=None, max_length=200)
    criticality: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class MasterDataSpecialist:
    def __init__(self, session: Session):
        self.agent = MasterDataAgent(session)

    @property
    def definition(self) -> AgentToolDefinition:
        return AgentToolDefinition(
            name="search_equipment_master",
            description=(
                "List or search equipment stored in the equipment master. "
                "Search by equipment number, description, type, functional "
                "location, system, or criticality; apply optional exact "
                "filters; and return paginated records plus matching summary "
                "counts. Use this when the user asks what equipment exists "
                "or needs equipment identifiers before another analysis."
            ),
            input_schema=EquipmentSearchArguments.model_json_schema(),
        )

    def execute(
        self,
        arguments: dict[str, object],
        progress: ProgressCallback | None = None,
    ) -> str:
        request = EquipmentSearchArguments.model_validate(arguments)
        findings = self.agent.search_equipment(
            query=request.query,
            equipment_type=request.equipment_type,
            functional_location=request.functional_location,
            criticality=request.criticality,
            status=request.status,
            limit=request.limit,
            offset=request.offset,
            progress=progress,
        )
        response = EquipmentSearchResponse.model_validate(
            findings,
            from_attributes=True,
        )
        return response.model_dump_json()


class MaintenanceStrategyReviewArguments(BaseModel):
    equipment_numbers: list[str] = Field(
        default_factory=list,
        max_length=10,
    )
    include_failure_history: bool = True
    maximum_assets: int = Field(default=5, ge=1, le=10)


class MaintenanceStrategySpecialist:
    def __init__(self, session: Session):
        self.agent = MaintenanceStrategyAgent(session)

    @property
    def definition(self) -> AgentToolDefinition:
        return AgentToolDefinition(
            name="review_maintenance_strategy",
            description=(
                "Review stored maintenance strategies against equipment "
                "criticality, work-order history, costs, downtime, and "
                "observed failure modes. Identify supported tasks, weak "
                "failure-mode coverage, frequency risks, strategy gaps, and "
                "condition-monitoring opportunities. Use this when the user "
                "asks whether maintenance plans are adequate or how they "
                "should change."
            ),
            input_schema=MaintenanceStrategyReviewArguments.model_json_schema(),
        )

    def execute(
        self,
        arguments: dict[str, object],
        progress: ProgressCallback | None = None,
    ) -> str:
        request = MaintenanceStrategyReviewArguments.model_validate(arguments)
        findings = self.agent.review(
            equipment_numbers=request.equipment_numbers,
            include_failure_history=request.include_failure_history,
            maximum_assets=request.maximum_assets,
            progress=progress,
        )
        response = MaintenanceStrategyReviewResponse.model_validate(
            findings,
            from_attributes=True,
        )

        return response.model_dump_json()


class SpecialistRegistry:
    def __init__(
        self,
        session: Session,
        specialists: Sequence[Specialist] | None = None,
    ):
        registered = (
            specialists
            if specialists is not None
            else (
                MasterDataSpecialist(session),
                DefectEliminationSpecialist(session),
                MaintenanceStrategySpecialist(session),
            )
        )
        self._specialists = {
            specialist.definition.name: specialist
            for specialist in registered
        }

    @property
    def definitions(self) -> tuple[AgentToolDefinition, ...]:
        return tuple(
            specialist.definition
            for specialist in self._specialists.values()
        )

    def execute(
        self,
        call: AgentToolCall,
        progress: ProgressCallback | None = None,
    ) -> AgentToolResult:
        specialist = self._specialists.get(call.name)

        if specialist is None:
            return AgentToolResult(
                call_id=call.id,
                tool_name=call.name,
                content=f"Unknown specialist capability: {call.name}.",
                is_error=True,
            )

        try:
            content = specialist.execute(call.arguments, progress)
        except ValidationError as error:
            content = (
                "The specialist arguments were invalid: "
                f"{error.errors(include_url=False)}"
            )
            return AgentToolResult(
                call_id=call.id,
                tool_name=call.name,
                content=content,
                is_error=True,
            )
        except Exception:
            return AgentToolResult(
                call_id=call.id,
                tool_name=call.name,
                content=(
                    "The specialist could not complete the analysis. "
                    "Continue using any other available evidence and explain "
                    "the limitation."
                ),
                is_error=True,
            )

        return AgentToolResult(
            call_id=call.id,
            tool_name=call.name,
            content=content,
        )
