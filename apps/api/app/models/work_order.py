import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.equipment import Equipment
    from app.models.import_batch import ImportBatch
    from app.models.work_order_failure_mode import WorkOrderFailureMode


MaintenanceActivityType = Literal[
    "corrective",
    "preventive",
    "emergency",
    "inspection",
    "condition_monitoring",
    "other",
    "unknown",
]


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint(
            "maintenance_activity_type IN ('corrective', 'preventive', "
            "'emergency', 'inspection', 'condition_monitoring', 'other', "
            "'unknown')",
            name="ck_work_orders_maintenance_activity_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    order_number: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )

    notification_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipment.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    functional_location: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    order_type: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    status: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    priority: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    maintenance_activity_type: Mapped[MaintenanceActivityType] = mapped_column(
        Text,
        nullable=False,
        default="unknown",
    )

    short_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    long_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at_source: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    required_by_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    total_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    downtime_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
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

    equipment: Mapped["Equipment | None"] = relationship(
        back_populates="work_orders",
    )

    import_batch: Mapped["ImportBatch | None"] = relationship(
        back_populates="work_orders",
    )

    failure_mode_links: Mapped[list["WorkOrderFailureMode"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
    )
