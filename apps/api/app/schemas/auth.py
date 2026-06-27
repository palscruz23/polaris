import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None
    avatar_url: str | None
    auth_provider: str
    created_at: datetime
