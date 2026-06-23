from fastapi import APIRouter

from app.providers.models import AVAILABLE_MODELS, DEFAULT_MODEL_ID
from app.schemas.model import AvailableModelResponse

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("", response_model=list[AvailableModelResponse])
def list_models() -> list[AvailableModelResponse]:
    return [
        AvailableModelResponse(
            id=model.id,
            label=model.label,
            is_default=model.id == DEFAULT_MODEL_ID,
            is_enabled=model.enabled,
        )
        for model in AVAILABLE_MODELS
    ]
