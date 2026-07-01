import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


ScheduledReviewTemplateId = Literal[
    "breakdown_strategy_gap",
    "bad_actor_watchlist",
    "maintenance_strategy_health_check",
]
ScheduledReviewRunStatus = Literal[
    "running",
    "succeeded",
    "partially_succeeded",
    "failed",
]
ScheduledReviewDeliveryProvider = Literal["teams"]
ScheduledReviewDeliveryStatus = Literal["pending", "sent", "failed"]


class ScheduledReviewRun(Base):
    __tablename__ = "scheduled_review_runs"
    __table_args__ = (
        CheckConstraint(
            "template_id IN ('breakdown_strategy_gap', "
            "'bad_actor_watchlist', 'maintenance_strategy_health_check')",
            name="ck_scheduled_review_runs_template_id",
        ),
        CheckConstraint(
            "status IN ('running', 'succeeded', 'partially_succeeded', "
            "'failed')",
            name="ck_scheduled_review_runs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    template_id: Mapped[ScheduledReviewTemplateId] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    status: Mapped[ScheduledReviewRunStatus] = mapped_column(
        Text,
        nullable=False,
        default="running",
    )
    window_start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    window_end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    report_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    deliveries: Mapped[list["ScheduledReviewDelivery"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ScheduledReviewDelivery.created_at",
    )


class ScheduledReviewDelivery(Base):
    __tablename__ = "scheduled_review_deliveries"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('teams')",
            name="ck_scheduled_review_deliveries_provider",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_scheduled_review_deliveries_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scheduled_review_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scheduled_review_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[ScheduledReviewDeliveryProvider] = mapped_column(
        Text,
        nullable=False,
    )
    destination_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ScheduledReviewDeliveryStatus] = mapped_column(
        Text,
        nullable=False,
        default="pending",
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    provider_response_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped[ScheduledReviewRun] = relationship(back_populates="deliveries")
