from pydantic import BaseModel


class AvailableModelResponse(BaseModel):
    id: str
    label: str
    is_default: bool
    is_enabled: bool
