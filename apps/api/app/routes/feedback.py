from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.dependencies.auth import CurrentUser
from app.models.feedback_response import FeedbackResponse as FeedbackResponseModel
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_feedback(
    request: FeedbackCreate,
    session: DatabaseSession,
    user: CurrentUser,
) -> FeedbackResponse:
    if request.conversation_id is not None:
        conversation = ConversationRepository(session).get_by_id(
            request.conversation_id,
            user_id=user.id,
        )
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

    feedback = FeedbackResponseModel(
        user_id=user.id,
        conversation_id=request.conversation_id,
        usefulness_rating=request.usefulness_rating,
        confidence_rating=request.confidence_rating,
        most_useful=request.most_useful,
        improvement_priority=request.improvement_priority,
        future_feature_interest=list(request.future_feature_interest),
        comment=request.comment,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)

    return feedback
