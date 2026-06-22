import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch
    from app.models.work_order_failure_mode import WorkOrderFailureMode


class FailureMode(Base):
    __tablename__ = "failure_modes"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "equipment_type",
            name="uq_failure_modes_name_equipment_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    equipment_type: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    mechanism: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    cause: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    symptom: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    consequence_category: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    import_batch: Mapped["ImportBatch | None"] = relationship(
        back_populates="failure_modes",
    )

    work_order_links: Mapped[list["WorkOrderFailureMode"]] = relationship(
        back_populates="failure_mode",
        cascade="all, delete-orphan",
    )
