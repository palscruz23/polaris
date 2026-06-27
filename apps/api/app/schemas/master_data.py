from pydantic import BaseModel, ConfigDict


class EquipmentSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_matching: int
    returned_count: int
    offset: int
    limit: int
    has_more: bool
    status_counts: dict[str, int]
    equipment_type_counts: dict[str, int]


class EquipmentRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_number: str
    description: str | None
    functional_location: str | None
    equipment_type: str | None
    system: str | None
    criticality: str | None
    status: str
    parent_functional_location: str | None


class EquipmentSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: EquipmentSummaryResponse
    equipment: list[EquipmentRecordResponse]
