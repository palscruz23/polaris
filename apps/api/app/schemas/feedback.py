import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MostUsefulOption = Literal[
    "repeat_failures",
    "maintenance_strategy_review",
    "equipment_data_search",
    "recommendations_next_actions",
    "conversation_memory_context",
    "other",
]

ImprovementPriorityOption = Literal[
    "data_accuracy",
    "more_detailed_evidence",
    "better_recommendations",
    "upload_import_workflow",
    "faster_responses",
    "easier_ui",
    "other",
]

FutureFeatureOption = Literal[
    "knowledge_base",
    "configure_subagent_model_selection",
    "upload_data",
    "additional_subagent",
    "additional_tools",
]


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    conversation_id: uuid.UUID | None = None
    usefulness_rating: int | None = Field(default=None, ge=1, le=5)
    confidence_rating: int | None = Field(default=None, ge=1, le=5)
    most_useful: MostUsefulOption | None = None
    improvement_priority: ImprovementPriorityOption | None = None
    future_feature_interest: list[FutureFeatureOption] = Field(default_factory=list)
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    conversation_id: uuid.UUID | None
    usefulness_rating: int | None
    confidence_rating: int | None
    most_useful: str | None
    improvement_priority: str | None
    future_feature_interest: list[str] | None
    comment: str | None
    source: str
    created_at: datetime
