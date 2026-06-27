import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.user import User


class FeedbackResponse(Base):
    __tablename__ = "feedback_responses"
    __table_args__ = (
        CheckConstraint(
            "usefulness_rating IS NULL OR "
            "(usefulness_rating >= 1 AND usefulness_rating <= 5)",
            name="ck_feedback_responses_usefulness_rating",
        ),
        CheckConstraint(
            "confidence_rating IS NULL OR "
            "(confidence_rating >= 1 AND confidence_rating <= 5)",
            name="ck_feedback_responses_confidence_rating",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    usefulness_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    most_useful: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_priority: Mapped[str | None] = mapped_column(Text, nullable=True)
    future_feature_interest: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="poc_survey",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship()
    conversation: Mapped["Conversation | None"] = relationship()
