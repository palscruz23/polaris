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


StrategyType = Literal[
    "time_based",
    "condition_based",
    "inspection",
    "lubrication",
    "statutory",
    "other",
]
StrategyStatus = Literal["active", "inactive", "draft"]


class MaintenanceStrategy(Base):
    __tablename__ = "maintenance_strategies"
    __table_args__ = (
        CheckConstraint(
            "strategy_type IN ('time_based', 'condition_based', "
            "'inspection', 'lubrication', 'statutory', 'other')",
            name="ck_maintenance_strategies_strategy_type",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'draft')",
            name="ck_maintenance_strategies_status",
        ),
        CheckConstraint(
            "equipment_id IS NOT NULL OR functional_location IS NOT NULL",
            name="ck_maintenance_strategies_has_asset_reference",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    strategy_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    task_number: Mapped[str | None] = mapped_column(
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

    task_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    strategy_type: Mapped[StrategyType] = mapped_column(
        Text,
        nullable=False,
        default="other",
    )

    frequency_value: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    frequency_unit: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[StrategyStatus] = mapped_column(
        Text,
        nullable=False,
        default="active",
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
        back_populates="maintenance_strategies",
    )

    import_batch: Mapped["ImportBatch | None"] = relationship(
        back_populates="maintenance_strategies",
    )
