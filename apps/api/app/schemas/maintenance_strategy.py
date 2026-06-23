from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class MaintenanceStrategyTaskProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strategy_number: str | None
    task_number: str | None
    task_description: str
    strategy_type: str
    frequency_value: Decimal | None
    frequency_unit: str | None
    frequency_days: Decimal | None
    status: str


class MaintenanceStrategyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    equipment_description: str | None
    equipment_type: str | None
    criticality: str | None
    task_count: int
    active_task_count: int
    strategy_types: list[str]
    tasks: list[MaintenanceStrategyTaskProfileResponse]


class MaintenanceMixResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_work_orders: int
    corrective_work_orders: int
    emergency_work_orders: int
    preventive_work_orders: int
    inspection_work_orders: int
    condition_monitoring_work_orders: int
    corrective_preventive_ratio: Decimal | None
    total_cost: Decimal
    total_downtime_hours: Decimal


class FailureModeCoverageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    failure_mode: str
    occurrence_count: int
    coverage: Literal["covered", "partial", "uncovered"]
    matched_task_numbers: list[str]
    matched_task_descriptions: list[str]
    confidence: Literal["low", "medium", "high"]
    evidence_work_orders: list[str]


class FrequencyRiskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_number: str | None
    task_description: str
    frequency_days: Decimal | None
    related_failure_modes: list[str]
    observed_recurrence_days: Decimal | None
    risk: Literal["low", "medium", "high", "unknown"]
    reason: str


class MaintenanceStrategyGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gap_type: str
    failure_mode: str | None
    severity: Literal["low", "medium", "high", "unknown"]
    evidence: str
    recommendation: str


class ConditionMonitoringOpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    failure_mode: str
    monitoring_method: str
    rationale: str
    priority: Literal["low", "medium", "high", "unknown"]


class MaintenanceStrategyRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: Literal["keep", "modify", "add", "engineering_review"]
    task_number: str | None
    failure_mode: str | None
    priority: Literal["low", "medium", "high", "unknown"]
    reason: str
    suggestion: str


class AssetMaintenanceStrategyReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile: MaintenanceStrategyProfileResponse
    maintenance_mix: MaintenanceMixResponse
    failure_mode_coverage: list[FailureModeCoverageResponse]
    frequency_risks: list[FrequencyRiskResponse]
    strategy_gaps: list[MaintenanceStrategyGapResponse]
    condition_monitoring_opportunities: list[
        ConditionMonitoringOpportunityResponse
    ]
    recommendations: list[MaintenanceStrategyRecommendationResponse]


class MaintenanceStrategyReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reviewed_asset_count: int
    requested_equipment_numbers: list[str]
    missing_equipment_numbers: list[str]
    asset_reviews: list[AssetMaintenanceStrategyReviewResponse]
    limitations: list[str]
