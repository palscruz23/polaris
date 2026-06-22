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


class MTBFFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    equipment_description: str | None
    equipment_type: str | None
    corrective_event_count: int
    observation_days: Decimal | None
    mtbf_days: Decimal | None
    first_event_at: datetime | None
    last_event_at: datetime | None


class RCAEvidencePlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    failure_mode: str
    evidence_to_collect: list[str]
    people_to_interview: list[str]
    records_to_review: list[str]
    immediate_containment_actions: list[str]


class FiveWhysAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    failure_mode: str
    problem_statement: str
    whys: list[str]
    likely_root_cause_theme: str


class RCATemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    failure_mode: str
    title: str
    sections: list[str]
    starter_questions: list[str]


class DefectEliminationCharterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    failure_mode: str
    title: str
    problem_statement: str
    business_impact: str
    asset_context: str
    failure_pattern_summary: str
    hypotheses: list[str]
    required_evidence: list[str]
    recommended_actions: list[str]
    success_criteria: list[str]
    verification_plan: list[str]


class DefectEliminationOverviewResponse(BaseModel):
    summary: DefectEliminationSummaryResponse
    bad_actors: list[BadActorFindingResponse]
    repeat_failures: list[RepeatFailureFindingResponse]
    mtbf_metrics: list[MTBFFindingResponse]
    rca_evidence_plans: list[RCAEvidencePlanResponse]
    five_whys: list[FiveWhysAnalysisResponse]
    rca_templates: list[RCATemplateResponse]
    charters: list[DefectEliminationCharterResponse]
    recommendations: list[str]
