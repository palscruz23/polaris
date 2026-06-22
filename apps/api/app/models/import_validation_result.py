import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch


ValidationSeverity = Literal["info", "warning", "error"]


class ImportValidationResult(Base):
    __tablename__ = "import_validation_results"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'error')",
            name="ck_import_validation_results_severity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    severity: Mapped[ValidationSeverity] = mapped_column(
        Text,
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_column: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_row_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    import_batch: Mapped["ImportBatch"] = relationship(
        back_populates="validation_results",
    )
