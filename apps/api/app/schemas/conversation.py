import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.message import MessageResponse


class ConversationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(
        default=None,
        max_length=200,
    )


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    memory_markdown: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    memory_updated_at: datetime | None
    memory_through_sequence_number: int
    memory_update_status: str
    memory_update_error: str | None
    is_processing: bool
    processing_started_at: datetime | None
    messages: list[MessageResponse] = Field(default_factory=list)


class ConversationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime
    is_processing: bool
