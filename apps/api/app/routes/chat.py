from fastapi import APIRouter, HTTPException, status

from app.services.chat_service import ChatServiceError, generate_response
from app.schemas.RequestSchema import ChatRequest, ChatResponse


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
def chat(request: ChatRequest) -> ChatResponse:
    try:
        response = generate_response(request.message)
    except ChatServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    return {
        "message": request.message,
        "response": response,
    }