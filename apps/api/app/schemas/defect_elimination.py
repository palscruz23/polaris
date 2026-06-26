from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DefectEliminationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_work_orders: int
    corrective_work_orders: int
    emergency_work_orders: int
    preventive_work_orders: int
    condition_monitoring_work_orders: int
    total_cost: Decimal
    total_downtime_hours: Decimal
    first_work_order_at: datetime | None
    last_work_order_at: datetime | None
    corrective_preventive_ratio: Decimal | None


class BadActorFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    equipment_description: str | None
    equipment_type: str | None
    functional_location: str | None
    criticality: str | None
    total_work_orders: int
    corrective_work_orders: int
    emergency_work_orders: int
    preventive_work_orders: int
    total_cost: Decimal
    total_downtime_hours: Decimal
    mttr_hours: Decimal | None
    corrective_event_count: int
    observation_days: Decimal | None
    mtbf_days: Decimal | None
    first_event_at: datetime | None
    last_event_at: datetime | None
    score: Decimal


class RepeatFailureFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    equipment_description: str | None
    failure_mode: str
    equipment_type: str | None
    work_order_count: int
    total_cost: Decimal
    total_downtime_hours: Decimal
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    evidence: str


class FailureModeBadActorFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    equipment_description: str | None
    failure_mode: str
    equipment_type: str | None
    repeat_work_order_count: int
    total_cost: Decimal
    total_downtime_hours: Decimal
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    evidence: str
    score: Decimal


class DefectEliminationOverviewResponse(BaseModel):
    summary: DefectEliminationSummaryResponse
    bad_actors: list[BadActorFindingResponse]
    repeat_failures: list[RepeatFailureFindingResponse]
    failure_mode_bad_actors: list[FailureModeBadActorFindingResponse]
    recommendations: list[str]
