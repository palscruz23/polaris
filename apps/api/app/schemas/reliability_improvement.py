from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ReliabilityImprovementOpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    equipment_description: str | None
    equipment_type: str | None
    criticality: str | None
    opportunity_type: str
    priority: Literal["low", "medium", "high"]
    estimated_annual_value: Decimal
    value_basis: str
    evidence: list[str]


class ReliabilityImprovementActionPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    title: str
    owner_role: str
    priority: Literal["low", "medium", "high"]
    actions: list[str]
    milestones: list[str]
    deliverables: list[str]


class ReliabilityImprovementOutcomeReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    success_measures: list[str]
    baseline_summary: str
    expected_outcome: str
    reporting_cadence: str


class ReliabilityImprovementRoadmapItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    title: str
    horizon: Literal["now", "next", "later"]
    priority: Literal["low", "medium", "high"]
    rationale: str
    dependencies: list[str]


class ReliabilityImprovementPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunities: list[ReliabilityImprovementOpportunityResponse]
    action_plans: list[ReliabilityImprovementActionPlanResponse]
    outcome_reports: list[ReliabilityImprovementOutcomeReportResponse]
    roadmap: list[ReliabilityImprovementRoadmapItemResponse]
    limitations: list[str]
