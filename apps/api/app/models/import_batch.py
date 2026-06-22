import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import CheckConstraint, DateTime, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.equipment import Equipment
    from app.models.failure_mode import FailureMode
    from app.models.import_validation_result import ImportValidationResult
    from app.models.maintenance_strategy import MaintenanceStrategy
    from app.models.work_order import WorkOrder


DatasetType = Literal[
    "equipment",
    "work_orders",
    "maintenance_strategies",
    "failure_modes",
]
ImportStatus = Literal["pending", "completed", "failed"]


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "dataset_type IN ('equipment', 'work_orders', "
            "'maintenance_strategies', 'failure_modes')",
            name="ck_import_batches_dataset_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_import_batches_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    dataset_type: Mapped[DatasetType] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[ImportStatus] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    record_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    equipment_records: Mapped[list["Equipment"]] = relationship(
        back_populates="import_batch",
    )

    work_orders: Mapped[list["WorkOrder"]] = relationship(
        back_populates="import_batch",
    )

    maintenance_strategies: Mapped[list["MaintenanceStrategy"]] = relationship(
        back_populates="import_batch",
    )

    failure_modes: Mapped[list["FailureMode"]] = relationship(
        back_populates="import_batch",
    )

    validation_results: Mapped[list["ImportValidationResult"]] = relationship(
        back_populates="import_batch",
        cascade="all, delete-orphan",
        order_by="ImportValidationResult.created_at",
    )
