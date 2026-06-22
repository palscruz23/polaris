import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch
    from app.models.maintenance_strategy import MaintenanceStrategy
    from app.models.work_order import WorkOrder


EquipmentStatus = Literal["active", "inactive", "decommissioned", "unknown"]


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'decommissioned', 'unknown')",
            name="ck_equipment_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    equipment_number: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )

    functional_location: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    parent_equipment_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    parent_functional_location: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    equipment_type: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    system: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    criticality: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    status: Mapped[EquipmentStatus] = mapped_column(
        Text,
        nullable=False,
        default="unknown",
    )

    install_date: Mapped[date | None] = mapped_column(
        Date,
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

    import_batch: Mapped["ImportBatch | None"] = relationship(
        back_populates="equipment_records",
    )

    work_orders: Mapped[list["WorkOrder"]] = relationship(
        back_populates="equipment",
    )

    maintenance_strategies: Mapped[list["MaintenanceStrategy"]] = relationship(
        back_populates="equipment",
    )
