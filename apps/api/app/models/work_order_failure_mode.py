import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.failure_mode import FailureMode
    from app.models.work_order import WorkOrder


FailureModeLinkSource = Literal["user", "rule", "agent", "import"]


class WorkOrderFailureMode(Base):
    __tablename__ = "work_order_failure_modes"
    __table_args__ = (
        CheckConstraint(
            "source IN ('user', 'rule', 'agent', 'import')",
            name="ck_work_order_failure_modes_source",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_work_order_failure_modes_confidence_range",
        ),
        UniqueConstraint(
            "work_order_id",
            "failure_mode_id",
            name="uq_work_order_failure_modes_work_order_failure_mode",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("work_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    failure_mode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("failure_modes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source: Mapped[FailureModeLinkSource] = mapped_column(
        Text,
        nullable=False,
        default="import",
    )

    confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
    )

    evidence: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    work_order: Mapped["WorkOrder"] = relationship(
        back_populates="failure_mode_links",
    )

    failure_mode: Mapped["FailureMode"] = relationship(
        back_populates="work_order_links",
    )
