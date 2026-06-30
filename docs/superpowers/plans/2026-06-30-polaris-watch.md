# Polaris Watch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Polaris Watch v1: daily GitHub Actions jobs that import work-order data, run three predefined reliability review templates, and send one Microsoft Teams report per template.

**Architecture:** GitHub Actions owns scheduling. Backend CLI commands own import and review execution. The review path uses existing Defect Elimination and Maintenance Strategy agents, persists review/delivery history, and sends Teams notifications through a provider interface that can later support Webex.

**Tech Stack:** FastAPI backend package, Python 3.11, SQLAlchemy ORM, Alembic, pytest, httpx, GitHub Actions cron.

---

## File Structure

- Create `apps/api/app/models/scheduled_review.py`: SQLAlchemy models for Polaris Watch review runs and notification deliveries.
- Modify `apps/api/app/models/__init__.py`: export the new models.
- Create `apps/api/alembic/versions/b8c9d0e1f234_create_scheduled_review_tables.py`: migration for `scheduled_review_runs` and `scheduled_review_deliveries`.
- Modify `apps/api/app/config.py`: add Teams webhook and Polaris Watch default settings.
- Modify `apps/api/.env.example`: document new environment variables.
- Create `apps/api/app/services/daily_reliability_import_service.py`: incremental import service for daily work orders and failure-mode links.
- Create `apps/api/app/cli/import_daily_reliability_data.py`: CLI wrapper for the import service.
- Create `apps/api/app/services/scheduled_review_service.py`: template selection and review orchestration.
- Create `apps/api/app/services/scheduled_review_report_builder.py`: report formatting.
- Create `apps/api/app/services/notification_delivery.py`: delivery interface and Teams implementation.
- Create `apps/api/app/cli/run_scheduled_review.py`: CLI wrapper for one review template.
- Create `.github/workflows/polaris-watch-import.yml`: daily import cron.
- Create `.github/workflows/polaris-watch-breakdown-strategy-gap.yml`: daily breakdown strategy gap review cron.
- Create `.github/workflows/polaris-watch-bad-actor-watchlist.yml`: daily bad actor watchlist cron.
- Create `.github/workflows/polaris-watch-maintenance-strategy-health-check.yml`: daily maintenance strategy health check cron.
- Create tests under `apps/api/tests/` for import, review service, report builder, notification delivery, and CLI behavior.

## Task 1: Persist Polaris Watch Runs

**Files:**
- Create: `apps/api/app/models/scheduled_review.py`
- Modify: `apps/api/app/models/__init__.py`
- Create: `apps/api/alembic/versions/b8c9d0e1f234_create_scheduled_review_tables.py`
- Test: `apps/api/tests/test_scheduled_review_models.py`

- [ ] **Step 1: Write model export test**

Create `apps/api/tests/test_scheduled_review_models.py`:

```python
from app.models import ScheduledReviewDelivery, ScheduledReviewRun


def test_scheduled_review_models_are_exported() -> None:
    assert ScheduledReviewRun.__tablename__ == "scheduled_review_runs"
    assert ScheduledReviewDelivery.__tablename__ == "scheduled_review_deliveries"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd apps/api
python -m pytest tests/test_scheduled_review_models.py -v
```

Expected: FAIL because `ScheduledReviewRun` and `ScheduledReviewDelivery` are not exported.

- [ ] **Step 3: Add SQLAlchemy models**

Create `apps/api/app/models/scheduled_review.py`:

```python
from datetime import datetime
import uuid
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
```

- [ ] **Step 4: Export the models**

Modify `apps/api/app/models/__init__.py`:

```python
from app.models.scheduled_review import ScheduledReviewDelivery, ScheduledReviewRun
```

Add both names to `__all__`.

- [ ] **Step 5: Add Alembic migration**

Create `apps/api/alembic/versions/b8c9d0e1f234_create_scheduled_review_tables.py`:

```python
"""create scheduled review tables

Revision ID: b8c9d0e1f234
Revises: e6f7a8b9c012
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f234"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_review_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("window_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_markdown", sa.Text(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "template_id IN ('breakdown_strategy_gap', "
            "'bad_actor_watchlist', 'maintenance_strategy_health_check')",
            name="ck_scheduled_review_runs_template_id",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'partially_succeeded', "
            "'failed')",
            name="ck_scheduled_review_runs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scheduled_review_runs_template_id"),
        "scheduled_review_runs",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_review_runs_window_start_at"),
        "scheduled_review_runs",
        ["window_start_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_review_runs_window_end_at"),
        "scheduled_review_runs",
        ["window_end_at"],
        unique=False,
    )

    op.create_table(
        "scheduled_review_deliveries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scheduled_review_run_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("destination_label", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_response_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('teams')",
            name="ck_scheduled_review_deliveries_provider",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_scheduled_review_deliveries_status",
        ),
        sa.ForeignKeyConstraint(
            ["scheduled_review_run_id"],
            ["scheduled_review_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scheduled_review_deliveries_scheduled_review_run_id"),
        "scheduled_review_deliveries",
        ["scheduled_review_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_scheduled_review_deliveries_scheduled_review_run_id"),
        table_name="scheduled_review_deliveries",
    )
    op.drop_table("scheduled_review_deliveries")
    op.drop_index(
        op.f("ix_scheduled_review_runs_window_end_at"),
        table_name="scheduled_review_runs",
    )
    op.drop_index(
        op.f("ix_scheduled_review_runs_window_start_at"),
        table_name="scheduled_review_runs",
    )
    op.drop_index(
        op.f("ix_scheduled_review_runs_template_id"),
        table_name="scheduled_review_runs",
    )
    op.drop_table("scheduled_review_runs")
```

- [ ] **Step 6: Run the model test**

Run:

```bash
cd apps/api
python -m pytest tests/test_scheduled_review_models.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/models/scheduled_review.py apps/api/app/models/__init__.py apps/api/alembic/versions/b8c9d0e1f234_create_scheduled_review_tables.py apps/api/tests/test_scheduled_review_models.py
git commit -m "Add Polaris Watch persistence models"
```

## Task 2: Add Polaris Watch Configuration

**Files:**
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/.env.example`
- Test: `apps/api/tests/test_config.py`

- [ ] **Step 1: Write config tests**

Append to `apps/api/tests/test_config.py`:

```python
from app.config import build_cors_origins, normalize_optional_url
```

If these imports already exist, keep only one import line. Add tests:

```python
def test_polaris_watch_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@host/db")
    monkeypatch.setenv(
        "SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL",
        "https://example.test/teams",
    )
    monkeypatch.setenv(
        "SCHEDULED_REVIEW_TEAMS_DESTINATION_LABEL",
        "Reliability Standup",
    )
    monkeypatch.setenv("SCHEDULED_REVIEW_DEFAULT_TIMEZONE", "Australia/Perth")

    from app.config import load_settings

    loaded = load_settings()

    assert loaded.scheduled_review_teams_webhook_url == "https://example.test/teams"
    assert loaded.scheduled_review_teams_destination_label == "Reliability Standup"
    assert loaded.scheduled_review_default_timezone == "Australia/Perth"
```

- [ ] **Step 2: Run config test to verify it fails**

Run:

```bash
cd apps/api
python -m pytest tests/test_config.py::test_polaris_watch_settings_load_from_environment -v
```

Expected: FAIL because the settings fields do not exist.

- [ ] **Step 3: Add settings fields**

Modify `apps/api/app/config.py`.

Add fields to `Settings`:

```python
    scheduled_review_teams_webhook_url: str | None
    scheduled_review_teams_destination_label: str
    scheduled_review_default_timezone: str
```

Add values inside `load_settings()`:

```python
        scheduled_review_teams_webhook_url=normalize_optional_url(
            os.getenv("SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL")
        ),
        scheduled_review_teams_destination_label=os.getenv(
            "SCHEDULED_REVIEW_TEAMS_DESTINATION_LABEL",
            "Reliability Team",
        ),
        scheduled_review_default_timezone=os.getenv(
            "SCHEDULED_REVIEW_DEFAULT_TIMEZONE",
            "Australia/Sydney",
        ),
```

- [ ] **Step 4: Document environment variables**

Append to `apps/api/.env.example`:

```env
SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL=
SCHEDULED_REVIEW_TEAMS_DESTINATION_LABEL=Reliability Team
SCHEDULED_REVIEW_DEFAULT_TIMEZONE=Australia/Sydney
```

- [ ] **Step 5: Run config tests**

Run:

```bash
cd apps/api
python -m pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/config.py apps/api/.env.example apps/api/tests/test_config.py
git commit -m "Add Polaris Watch configuration"
```

## Task 3: Implement Daily Reliability Data Import

**Files:**
- Create: `apps/api/app/services/daily_reliability_import_service.py`
- Create: `apps/api/app/cli/import_daily_reliability_data.py`
- Test: `apps/api/tests/test_daily_reliability_import_service.py`

- [ ] **Step 1: Write import service tests**

Create `apps/api/tests/test_daily_reliability_import_service.py`:

```python
from pathlib import Path
from typing import Any

import pytest

from app.models import Equipment, FailureMode, ImportBatch, WorkOrder
from app.services.daily_reliability_import_service import (
    DailyReliabilityImportError,
    DailyReliabilityImportService,
)


class FakeSession:
    def __init__(
        self,
        existing: list[Any] | None = None,
        scalar_results: list[Any] | None = None,
    ) -> None:
        self.items = existing or []
        self.scalar_results = scalar_results or []
        self.added: list[Any] = []
        self.commit_count = 0

    def add(self, item: Any) -> None:
        self.added.append(item)
        self.items.append(item)

    def scalar(self, statement: Any) -> Any:
        if self.scalar_results:
            return self.scalar_results.pop(0)
        return None

    def commit(self) -> None:
        self.commit_count += 1


def test_daily_import_upserts_work_orders_and_failure_mode_links(tmp_path: Path) -> None:
    equipment = Equipment(equipment_number="P-101", equipment_type="pump")
    failure_mode = FailureMode(name="Seal leakage", equipment_type="pump")
    session = FakeSession([equipment, failure_mode])
    work_orders_csv = tmp_path / "work_orders.csv"
    links_csv = tmp_path / "work_order_failure_modes.csv"
    work_orders_csv.write_text(
        "order_number,notification_number,equipment_number,functional_location,"
        "order_type,status,priority,maintenance_activity_type,short_text,"
        "long_text,created_at_source,required_by_at,started_at,finished_at,"
        "total_cost,downtime_hours\n"
        "WO-1,,P-101,PLANT/PUMP,CM,closed,high,corrective,Repair seal,"
        "Seal leak,2026-06-29T00:00:00+00:00,,,,2026-06-29T02:00:00+00:00,1000,2\n",
        encoding="utf-8",
    )
    links_csv.write_text(
        "order_number,failure_mode_name,equipment_type,source,confidence,evidence\n"
        "WO-1,Seal leakage,pump,import,0.900,WO text mentions seal leak\n",
        encoding="utf-8",
    )
    session.scalar_results = [None, equipment, failure_mode]

    summary = DailyReliabilityImportService(session).import_files(
        work_orders_csv,
        links_csv,
    )

    assert summary.work_order_count == 1
    assert summary.work_order_failure_mode_count == 1
    assert session.commit_count == 1
    assert any(isinstance(item, ImportBatch) for item in session.added)
    work_order = next(item for item in session.items if isinstance(item, WorkOrder))
    assert work_order.order_number == "WO-1"
    assert work_order.equipment is equipment
    assert work_order.failure_mode_links[0].failure_mode is failure_mode


def test_daily_import_fails_for_unknown_equipment(tmp_path: Path) -> None:
    session = FakeSession()
    work_orders_csv = tmp_path / "work_orders.csv"
    links_csv = tmp_path / "work_order_failure_modes.csv"
    work_orders_csv.write_text(
        "order_number,notification_number,equipment_number,functional_location,"
        "order_type,status,priority,maintenance_activity_type,short_text,"
        "long_text,created_at_source,required_by_at,started_at,finished_at,"
        "total_cost,downtime_hours\n"
        "WO-1,,P-404,PLANT/PUMP,CM,closed,high,corrective,Repair seal,"
        ",2026-06-29T00:00:00+00:00,,,,,\n",
        encoding="utf-8",
    )
    links_csv.write_text(
        "order_number,failure_mode_name,equipment_type,source,confidence,evidence\n",
        encoding="utf-8",
    )
    session.scalar_results = [None, None]

    with pytest.raises(DailyReliabilityImportError, match="Unknown equipment"):
        DailyReliabilityImportService(session).import_files(work_orders_csv, links_csv)
```

- [ ] **Step 2: Run import tests to verify they fail**

Run:

```bash
cd apps/api
python -m pytest tests/test_daily_reliability_import_service.py -v
```

Expected: FAIL because the service module does not exist.

- [ ] **Step 3: Implement the import service**

Create `apps/api/app/services/daily_reliability_import_service.py` with:

```python
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Equipment,
    FailureMode,
    ImportBatch,
    WorkOrder,
    WorkOrderFailureMode,
)


class DailyReliabilityImportError(Exception):
    """Raised when daily reliability input cannot be imported."""


@dataclass(frozen=True)
class DailyReliabilityImportSummary:
    work_order_count: int
    work_order_failure_mode_count: int


class DailyReliabilityImportService:
    def __init__(self, session: Session):
        self.session = session

    def import_files(
        self,
        work_orders_csv: Path,
        work_order_failure_modes_csv: Path,
    ) -> DailyReliabilityImportSummary:
        work_order_rows = _read_csv(work_orders_csv)
        link_rows = _read_csv(work_order_failure_modes_csv)
        batch = ImportBatch(
            source_name=f"{work_orders_csv}:{work_order_failure_modes_csv}",
            dataset_type="work_orders",
            status="completed",
            record_count=len(work_order_rows),
            completed_at=datetime.now(UTC),
        )
        self.session.add(batch)
        work_orders_by_number = self._upsert_work_orders(work_order_rows, batch)
        link_count = self._upsert_links(link_rows, work_orders_by_number)
        self.session.commit()
        return DailyReliabilityImportSummary(
            work_order_count=len(work_order_rows),
            work_order_failure_mode_count=link_count,
        )

    def _upsert_work_orders(
        self,
        rows: list[dict[str, str]],
        batch: ImportBatch,
    ) -> dict[str, WorkOrder]:
        work_orders_by_number: dict[str, WorkOrder] = {}
        for row in rows:
            order_number = _required(row, "order_number")
            work_order = self.session.scalar(
                select(WorkOrder).where(WorkOrder.order_number == order_number)
            )
            if work_order is None:
                work_order = WorkOrder(order_number=order_number)
                self.session.add(work_order)

            equipment = _resolve_equipment(self.session, row)
            work_order.notification_number = _optional(row, "notification_number")
            work_order.equipment = equipment
            work_order.functional_location = _optional(row, "functional_location")
            work_order.order_type = _optional(row, "order_type")
            work_order.status = _optional(row, "status")
            work_order.priority = _optional(row, "priority")
            work_order.maintenance_activity_type = (
                _optional(row, "maintenance_activity_type") or "unknown"
            )
            work_order.short_text = _optional(row, "short_text")
            work_order.long_text = _optional(row, "long_text")
            work_order.created_at_source = _parse_datetime(
                _optional(row, "created_at_source")
            )
            work_order.required_by_at = _parse_datetime(
                _optional(row, "required_by_at")
            )
            work_order.started_at = _parse_datetime(_optional(row, "started_at"))
            work_order.finished_at = _parse_datetime(_optional(row, "finished_at"))
            work_order.total_cost = _parse_decimal(_optional(row, "total_cost"))
            work_order.downtime_hours = _parse_decimal(
                _optional(row, "downtime_hours")
            )
            work_order.import_batch = batch
            work_orders_by_number[order_number] = work_order
        return work_orders_by_number

    def _upsert_links(
        self,
        rows: list[dict[str, str]],
        work_orders_by_number: dict[str, WorkOrder],
    ) -> int:
        count = 0
        for row in rows:
            order_number = _required(row, "order_number")
            work_order = work_orders_by_number.get(order_number)
            if work_order is None:
                raise DailyReliabilityImportError(
                    f"Unknown work order in failure-mode link: {order_number}"
                )
            failure_mode = _resolve_failure_mode(self.session, row)
            existing_link = next(
                (
                    link
                    for link in work_order.failure_mode_links
                    if link.failure_mode is failure_mode
                ),
                None,
            )
            if existing_link is None:
                existing_link = WorkOrderFailureMode(
                    work_order=work_order,
                    failure_mode=failure_mode,
                )
                self.session.add(existing_link)
            existing_link.source = _optional(row, "source") or "import"
            existing_link.confidence = _parse_decimal(_optional(row, "confidence"))
            existing_link.evidence = _optional(row, "evidence")
            count += 1
        return count


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise DailyReliabilityImportError(f"CSV file does not exist: {path}")
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _resolve_equipment(session: Session, row: dict[str, str]) -> Equipment | None:
    equipment_number = _optional(row, "equipment_number")
    if equipment_number is None:
        return None
    equipment = session.scalar(
        select(Equipment).where(Equipment.equipment_number == equipment_number)
    )
    if equipment is None:
        raise DailyReliabilityImportError(
            f"Unknown equipment number: {equipment_number}"
        )
    return equipment


def _resolve_failure_mode(session: Session, row: dict[str, str]) -> FailureMode:
    name = _required(row, "failure_mode_name")
    equipment_type = _optional(row, "equipment_type")
    failure_mode = session.scalar(
        select(FailureMode).where(
            FailureMode.name == name,
            FailureMode.equipment_type == equipment_type,
        )
    )
    if failure_mode is None:
        raise DailyReliabilityImportError(f"Unknown failure mode: {name}")
    return failure_mode


def _required(row: dict[str, str], field: str) -> str:
    value = _optional(row, field)
    if value is None:
        raise DailyReliabilityImportError(f"Missing required field: {field}")
    return value


def _optional(row: dict[str, str], field: str) -> str | None:
    value = row.get(field)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)
```

- [ ] **Step 4: Add import CLI**

Create `apps/api/app/cli/import_daily_reliability_data.py`:

```python
import argparse
from pathlib import Path

from app.database import SessionLocal
from app.services.daily_reliability_import_service import (
    DailyReliabilityImportError,
    DailyReliabilityImportService,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import daily Polaris Watch work-order data.",
    )
    parser.add_argument("--work-orders-csv", type=Path, required=True)
    parser.add_argument("--work-order-failure-modes-csv", type=Path, required=True)
    args = parser.parse_args()

    with SessionLocal() as session:
        try:
            summary = DailyReliabilityImportService(session).import_files(
                args.work_orders_csv,
                args.work_order_failure_modes_csv,
            )
        except DailyReliabilityImportError:
            session.rollback()
            raise

    print("Imported daily reliability data:")
    print(f"- Work orders: {summary.work_order_count}")
    print(
        "- Work order failure mode links: "
        f"{summary.work_order_failure_mode_count}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run import tests**

Run:

```bash
cd apps/api
python -m pytest tests/test_daily_reliability_import_service.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/services/daily_reliability_import_service.py apps/api/app/cli/import_daily_reliability_data.py apps/api/tests/test_daily_reliability_import_service.py
git commit -m "Add daily reliability data import"
```

## Task 4: Build Polaris Watch Report Formatting

**Files:**
- Create: `apps/api/app/services/scheduled_review_report_builder.py`
- Test: `apps/api/tests/test_scheduled_review_report_builder.py`

- [ ] **Step 1: Write report builder tests**

Create `apps/api/tests/test_scheduled_review_report_builder.py`:

```python
from datetime import UTC, datetime

from app.services.scheduled_review_report_builder import (
    ScheduledReviewReport,
    ScheduledReviewReportBuilder,
)


def test_report_builder_includes_required_sections() -> None:
    report = ScheduledReviewReportBuilder().build(
        template_id="bad_actor_watchlist",
        title="Bad Actor Watchlist",
        window_start_at=datetime(2026, 6, 29, tzinfo=UTC),
        window_end_at=datetime(2026, 6, 30, tzinfo=UTC),
        summary="3 assets require review.",
        key_findings=["P-101 has recurring seal leakage."],
        recommended_actions=["Open a defect elimination review for P-101."],
        evidence=["WO-1, WO-2"],
        limitations=["Synthetic sample data only."],
    )

    assert isinstance(report, ScheduledReviewReport)
    assert "# Bad Actor Watchlist" in report.markdown
    assert "## Key findings" in report.markdown
    assert "- P-101 has recurring seal leakage." in report.markdown
    assert report.summary_json["template_id"] == "bad_actor_watchlist"
    assert report.summary_json["finding_count"] == 1
```

- [ ] **Step 2: Run report test to verify it fails**

Run:

```bash
cd apps/api
python -m pytest tests/test_scheduled_review_report_builder.py -v
```

Expected: FAIL because the report builder does not exist.

- [ ] **Step 3: Implement report builder**

Create `apps/api/app/services/scheduled_review_report_builder.py`:

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScheduledReviewReport:
    markdown: str
    summary_json: dict


class ScheduledReviewReportBuilder:
    def build(
        self,
        template_id: str,
        title: str,
        window_start_at: datetime,
        window_end_at: datetime,
        summary: str,
        key_findings: list[str],
        recommended_actions: list[str],
        evidence: list[str],
        limitations: list[str],
    ) -> ScheduledReviewReport:
        markdown = "\n".join(
            [
                f"# {title}",
                "",
                f"Window: {window_start_at.isoformat()} to {window_end_at.isoformat()}",
                "",
                "## Executive summary",
                summary,
                "",
                "## Key findings",
                *_bullet_lines(key_findings),
                "",
                "## Recommended actions",
                *_bullet_lines(recommended_actions),
                "",
                "## Evidence",
                *_bullet_lines(evidence),
                "",
                "## Data limitations",
                *_bullet_lines(limitations),
                "",
            ]
        )
        return ScheduledReviewReport(
            markdown=markdown,
            summary_json={
                "template_id": template_id,
                "title": title,
                "window_start_at": window_start_at.isoformat(),
                "window_end_at": window_end_at.isoformat(),
                "finding_count": len(key_findings),
                "recommended_action_count": len(recommended_actions),
                "evidence_count": len(evidence),
            },
        )


def _bullet_lines(values: list[str]) -> list[str]:
    if not values:
        return ["- None."]
    return [f"- {value}" for value in values]
```

- [ ] **Step 4: Run report tests**

Run:

```bash
cd apps/api
python -m pytest tests/test_scheduled_review_report_builder.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/services/scheduled_review_report_builder.py apps/api/tests/test_scheduled_review_report_builder.py
git commit -m "Add Polaris Watch report builder"
```

## Task 5: Implement Review Template Orchestration

**Files:**
- Modify: `apps/api/app/agents/defect_elimination_agent.py`
- Create: `apps/api/app/services/scheduled_review_service.py`
- Test: `apps/api/tests/test_scheduled_review_service.py`
- Test: `apps/api/tests/test_defect_elimination_agent.py`

- [ ] **Step 1: Write service tests**

Create `apps/api/tests/test_scheduled_review_service.py`:

```python
from datetime import UTC, datetime, timedelta
from typing import Any

from app.models import ScheduledReviewRun
from app.services.scheduled_review_service import (
    ScheduledReviewService,
    resolve_review_window,
)


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commit_count = 0

    def add(self, item: Any) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.commit_count += 1


class FakeDeliveryService:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, markdown: str) -> dict:
        self.messages.append(markdown)
        return {"status_code": 202}


class FakeScheduledReviewService(ScheduledReviewService):
    def _build_report(self, template_id, window_start_at, window_end_at):
        from app.services.scheduled_review_report_builder import ScheduledReviewReport

        return ScheduledReviewReport(
            markdown=f"# {self.report_builder.title}",
            summary_json={"template_id": template_id},
        )


class FakeReportBuilder:
    title = "Bad Actor Watchlist"


def test_resolve_review_window_uses_utc_now() -> None:
    now = datetime(2026, 6, 30, 0, 0, tzinfo=UTC)

    start, end = resolve_review_window(lookback_days=7, now=now)

    assert start == now - timedelta(days=7)
    assert end == now


def test_service_persists_successful_review_run() -> None:
    session = FakeSession()
    delivery = FakeDeliveryService()
    service = FakeScheduledReviewService(
        session,  # type: ignore[arg-type]
        report_builder=FakeReportBuilder(),
        delivery_service=delivery,
    )

    run = service.run_template(
        template_id="bad_actor_watchlist",
        lookback_days=30,
        now=datetime(2026, 6, 30, tzinfo=UTC),
    )

    assert isinstance(run, ScheduledReviewRun)
    assert run.template_id == "bad_actor_watchlist"
    assert run.status == "succeeded"
    assert run.report_markdown == "# Bad Actor Watchlist"
    assert delivery.messages == ["# Bad Actor Watchlist"]
    assert session.commit_count == 2


class FailingDeliveryService:
    def send(self, markdown: str) -> dict:
        raise RuntimeError("Teams webhook rejected the report")


def test_service_marks_partial_success_when_delivery_fails() -> None:
    session = FakeSession()
    service = FakeScheduledReviewService(
        session,  # type: ignore[arg-type]
        report_builder=FakeReportBuilder(),
        delivery_service=FailingDeliveryService(),
    )

    run = service.run_template(
        template_id="bad_actor_watchlist",
        lookback_days=30,
        now=datetime(2026, 6, 30, tzinfo=UTC),
    )

    assert run.status == "partially_succeeded"
    assert run.report_markdown == "# Bad Actor Watchlist"
    assert "Teams webhook rejected" in run.deliveries[0].error_message
```

- [ ] **Step 2: Run service tests to verify they fail**

Run:

```bash
cd apps/api
python -m pytest tests/test_scheduled_review_service.py -v
```

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Add defect-elimination window filtering**

Append this test to `apps/api/tests/test_defect_elimination_agent.py`:

```python
def test_defect_elimination_agent_filters_work_orders_by_finished_window() -> None:
    asset = Equipment(equipment_number="PUMP-001", equipment_type="pump")
    session = FakeSession()
    session.added.extend(
        [
            _work_order("WO-1", asset, "corrective", "2026-06-29", 2),
            _work_order("WO-2", asset, "corrective", "2026-06-01", 2),
        ]
    )
    agent = DefectEliminationAgent(session)  # type: ignore[arg-type]

    findings = agent.analyze(
        window_start_at=datetime.fromisoformat("2026-06-28T00:00:00+00:00"),
        window_end_at=datetime.fromisoformat("2026-06-30T00:00:00+00:00"),
    )

    assert findings.summary.total_work_orders == 1
```

Modify `apps/api/app/agents/defect_elimination_agent.py`:

```python
from datetime import datetime
```

Add optional arguments to `analyze`:

```python
        window_start_at: datetime | None = None,
        window_end_at: datetime | None = None,
```

Add the same optional arguments to `build_overview` and pass them through to
`analyze`:

```python
        window_start_at: datetime | None = None,
        window_end_at: datetime | None = None,
```

```python
            window_start_at=window_start_at,
            window_end_at=window_end_at,
```

Apply the filter after equipment filtering:

```python
        work_orders = self._filter_work_orders_by_window(
            work_orders,
            window_start_at,
            window_end_at,
        )
```

Add this static method:

```python
    @staticmethod
    def _filter_work_orders_by_window(
        work_orders: list[WorkOrder],
        window_start_at: datetime | None,
        window_end_at: datetime | None,
    ) -> list[WorkOrder]:
        if window_start_at is None and window_end_at is None:
            return work_orders

        filtered = []
        for work_order in work_orders:
            occurred_at = work_order.finished_at or work_order.created_at_source
            if occurred_at is None:
                continue
            if window_start_at is not None and occurred_at < window_start_at:
                continue
            if window_end_at is not None and occurred_at >= window_end_at:
                continue
            filtered.append(work_order)
        return filtered
```

Run:

```bash
cd apps/api
python -m pytest tests/test_defect_elimination_agent.py::test_defect_elimination_agent_filters_work_orders_by_finished_window -v
```

Expected: PASS.

- [ ] **Step 4: Implement service skeleton and template dispatch**

Create `apps/api/app/services/scheduled_review_service.py`:

```python
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.agents.defect_elimination_agent import DefectEliminationAgent
from app.agents.maintenance_strategy_agent import MaintenanceStrategyAgent
from app.models import ScheduledReviewDelivery, ScheduledReviewRun
from app.services.scheduled_review_report_builder import (
    ScheduledReviewReportBuilder,
)


ScheduledReviewTemplateId = Literal[
    "breakdown_strategy_gap",
    "bad_actor_watchlist",
    "maintenance_strategy_health_check",
]

TEMPLATE_TITLES: dict[str, str] = {
    "breakdown_strategy_gap": "Breakdown Strategy Gap Review",
    "bad_actor_watchlist": "Bad Actor Watchlist",
    "maintenance_strategy_health_check": "Maintenance Strategy Health Check",
}


class ScheduledReviewService:
    def __init__(
        self,
        session: Session,
        report_builder: ScheduledReviewReportBuilder | None = None,
        delivery_service=None,
    ):
        self.session = session
        self.report_builder = report_builder or ScheduledReviewReportBuilder()
        self.delivery_service = delivery_service

    def run_template(
        self,
        template_id: ScheduledReviewTemplateId,
        lookback_days: int,
        now: datetime | None = None,
    ) -> ScheduledReviewRun:
        if template_id not in TEMPLATE_TITLES:
            raise ValueError(f"Unsupported scheduled review template: {template_id}")
        window_start_at, window_end_at = resolve_review_window(lookback_days, now)
        run = ScheduledReviewRun(
            template_id=template_id,
            status="running",
            window_start_at=window_start_at,
            window_end_at=window_end_at,
        )
        self.session.add(run)
        self.session.commit()

        try:
            report = self._build_report(template_id, window_start_at, window_end_at)
            run.report_markdown = report.markdown
            run.summary_json = report.summary_json
            if self.delivery_service is not None:
                try:
                    response = self.delivery_service.send(report.markdown)
                    run.deliveries.append(
                        ScheduledReviewDelivery(
                            provider="teams",
                            status="sent",
                            provider_response_json=response,
                        )
                    )
                    run.status = "succeeded"
                except Exception as delivery_error:
                    run.deliveries.append(
                        ScheduledReviewDelivery(
                            provider="teams",
                            status="failed",
                            error_message=str(delivery_error),
                        )
                    )
                    run.status = "partially_succeeded"
            else:
                run.status = "succeeded"
            run.finished_at = datetime.now(UTC)
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = datetime.now(UTC)
            raise
        finally:
            self.session.commit()

        return run

    def _build_report(
        self,
        template_id: str,
        window_start_at: datetime,
        window_end_at: datetime,
    ):
        if template_id == "breakdown_strategy_gap":
            return self._build_breakdown_strategy_gap_report(
                window_start_at,
                window_end_at,
            )
        if template_id == "bad_actor_watchlist":
            return self._build_bad_actor_watchlist_report(
                window_start_at,
                window_end_at,
            )
        return self._build_maintenance_strategy_health_check_report(
            window_start_at,
            window_end_at,
        )

    def _build_breakdown_strategy_gap_report(
        self,
        window_start_at: datetime,
        window_end_at: datetime,
    ):
        defect_findings = DefectEliminationAgent(self.session).analyze(
            intent="rank_failure_mode_bad_actors",
            bad_actor_limit=10,
            repeat_failure_limit=10,
            window_start_at=window_start_at,
            window_end_at=window_end_at,
        )
        equipment_numbers = [
            finding.equipment_number
            for finding in defect_findings.failure_mode_bad_actors[:10]
        ]
        strategy_findings = MaintenanceStrategyAgent(self.session).analyze(
            intent="detect_gaps",
            equipment_numbers=equipment_numbers,
            maximum_assets=10,
        )
        key_findings = [
            f"{finding.equipment_number}: {finding.failure_mode} "
            f"({finding.repeat_work_order_count} repeat work orders)"
            for finding in defect_findings.failure_mode_bad_actors[:5]
        ]
        recommended_actions = [
            review.recommendations[0].suggestion
            for review in strategy_findings.asset_reviews
            if review.recommendations
        ][:5]
        evidence = [
            finding.evidence
            for finding in defect_findings.failure_mode_bad_actors[:5]
            if finding.evidence
        ]
        return self.report_builder.build(
            template_id="breakdown_strategy_gap",
            title=TEMPLATE_TITLES["breakdown_strategy_gap"],
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            summary=(
                "Reviewed recent breakdown-like work orders for strategy "
                "coverage gaps."
            ),
            key_findings=key_findings,
            recommended_actions=recommended_actions,
            evidence=evidence,
            limitations=strategy_findings.limitations,
        )

    def _build_bad_actor_watchlist(
        self,
        window_start_at: datetime,
        window_end_at: datetime,
    ):
        findings = DefectEliminationAgent(self.session).build_overview(
            bad_actor_limit=10,
            repeat_failure_limit=10,
            window_start_at=window_start_at,
            window_end_at=window_end_at,
        )
        key_findings = [
            f"{finding.equipment_number}: downtime={finding.total_downtime_hours}, "
            f"cost={finding.total_cost}, corrective events={finding.corrective_event_count}"
            for finding in findings.bad_actors[:5]
        ]
        evidence = [
            finding.evidence
            for finding in findings.repeat_failures[:5]
            if finding.evidence
        ]
        return self.report_builder.build(
            template_id="bad_actor_watchlist",
            title=TEMPLATE_TITLES["bad_actor_watchlist"],
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            summary="Reviewed bad actors and repeat failures.",
            key_findings=key_findings,
            recommended_actions=findings.recommendations[:5],
            evidence=evidence,
            limitations=[],
        )

    def _build_maintenance_strategy_health_check_report(
        self,
        window_start_at: datetime,
        window_end_at: datetime,
    ):
        findings = MaintenanceStrategyAgent(self.session).review(maximum_assets=10)
        key_findings = [
            f"{review.profile.equipment_number}: "
            f"{len(review.strategy_gaps)} strategy gap(s), "
            f"{len(review.frequency_risks)} frequency risk(s)"
            for review in findings.asset_reviews
        ][:5]
        recommended_actions = [
            recommendation.suggestion
            for review in findings.asset_reviews
            for recommendation in review.recommendations
        ][:5]
        evidence = [
            gap.evidence
            for review in findings.asset_reviews
            for gap in review.strategy_gaps
        ][:5]
        return self.report_builder.build(
            template_id="maintenance_strategy_health_check",
            title=TEMPLATE_TITLES["maintenance_strategy_health_check"],
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            summary="Reviewed maintenance strategy health for high-risk assets.",
            key_findings=key_findings,
            recommended_actions=recommended_actions,
            evidence=evidence,
            limitations=findings.limitations,
        )


def resolve_review_window(
    lookback_days: int,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    end = now or datetime.now(UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    return end - timedelta(days=lookback_days), end
```

- [ ] **Step 5: Run service tests**

Run:

```bash
cd apps/api
python -m pytest tests/test_scheduled_review_service.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/agents/defect_elimination_agent.py apps/api/app/services/scheduled_review_service.py apps/api/tests/test_defect_elimination_agent.py apps/api/tests/test_scheduled_review_service.py
git commit -m "Add Polaris Watch review orchestration"
```

## Task 6: Implement Teams Notification Delivery

**Files:**
- Create: `apps/api/app/services/notification_delivery.py`
- Test: `apps/api/tests/test_notification_delivery.py`

- [ ] **Step 1: Write delivery tests**

Create `apps/api/tests/test_notification_delivery.py`:

```python
import httpx

from app.services.notification_delivery import TeamsNotificationProvider


class FakeResponse:
    status_code = 202
    text = "accepted"

    def raise_for_status(self) -> None:
        return None


def test_teams_provider_posts_markdown_message() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202, text="accepted")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = TeamsNotificationProvider(
        webhook_url="https://example.test/webhook",
        destination_label="Reliability Team",
        client=client,
    )

    result = provider.send("# Report")

    assert result["status_code"] == 202
    assert requests[0].url == "https://example.test/webhook"
    assert requests[0].headers["content-type"] == "application/json"
    assert b"# Report" in requests[0].content
```

- [ ] **Step 2: Run delivery test to verify it fails**

Run:

```bash
cd apps/api
python -m pytest tests/test_notification_delivery.py -v
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement Teams provider**

Create `apps/api/app/services/notification_delivery.py`:

```python
from typing import Protocol

import httpx


class NotificationDeliveryService(Protocol):
    def send(self, markdown: str) -> dict:
        """Send a notification and return provider response metadata."""


class TeamsNotificationProvider:
    def __init__(
        self,
        webhook_url: str,
        destination_label: str,
        client: httpx.Client | None = None,
    ):
        self.webhook_url = webhook_url
        self.destination_label = destination_label
        self.client = client or httpx.Client(timeout=20)

    def send(self, markdown: str) -> dict:
        response = self.client.post(
            self.webhook_url,
            json={
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": markdown,
                                    "wrap": True,
                                }
                            ],
                        },
                    }
                ],
            },
        )
        response.raise_for_status()
        return {
            "status_code": response.status_code,
            "destination_label": self.destination_label,
            "response_text": response.text[:500],
        }
```

- [ ] **Step 4: Run delivery tests**

Run:

```bash
cd apps/api
python -m pytest tests/test_notification_delivery.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/services/notification_delivery.py apps/api/tests/test_notification_delivery.py
git commit -m "Add Teams notification delivery"
```

## Task 7: Add Scheduled Review CLI

**Files:**
- Create: `apps/api/app/cli/run_scheduled_review.py`
- Test: `apps/api/tests/test_run_scheduled_review_cli.py`

- [ ] **Step 1: Write CLI tests**

Create `apps/api/tests/test_run_scheduled_review_cli.py`:

```python
from app.cli.run_scheduled_review import parse_args


def test_parse_args_accepts_template_and_lookback_days() -> None:
    args = parse_args(
        [
            "--template",
            "bad_actor_watchlist",
            "--lookback-days",
            "30",
        ]
    )

    assert args.template == "bad_actor_watchlist"
    assert args.lookback_days == 30
```

- [ ] **Step 2: Run CLI test to verify it fails**

Run:

```bash
cd apps/api
python -m pytest tests/test_run_scheduled_review_cli.py -v
```

Expected: FAIL because the CLI module does not exist.

- [ ] **Step 3: Implement CLI**

Create `apps/api/app/cli/run_scheduled_review.py`:

```python
import argparse

from app.config import settings
from app.database import SessionLocal
from app.services.notification_delivery import TeamsNotificationProvider
from app.services.scheduled_review_service import ScheduledReviewService


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one Polaris Watch scheduled review template.",
    )
    parser.add_argument(
        "--template",
        choices=[
            "breakdown_strategy_gap",
            "bad_actor_watchlist",
            "maintenance_strategy_health_check",
        ],
        required=True,
    )
    parser.add_argument("--lookback-days", type=int, required=True)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if not settings.scheduled_review_teams_webhook_url:
        raise RuntimeError("SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL is not configured.")
    delivery = TeamsNotificationProvider(
        webhook_url=settings.scheduled_review_teams_webhook_url,
        destination_label=settings.scheduled_review_teams_destination_label,
    )
    with SessionLocal() as session:
        run = ScheduledReviewService(
            session,
            delivery_service=delivery,
        ).run_template(
            template_id=args.template,
            lookback_days=args.lookback_days,
        )

    print(
        f"{run.template_id}: {run.status} "
        f"window={run.window_start_at.isoformat()}..{run.window_end_at.isoformat()} "
        f"run={run.id}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
cd apps/api
python -m pytest tests/test_run_scheduled_review_cli.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/cli/run_scheduled_review.py apps/api/tests/test_run_scheduled_review_cli.py
git commit -m "Add Polaris Watch scheduled review CLI"
```

## Task 8: Add GitHub Actions Cron Workflows

**Files:**
- Create: `.github/workflows/polaris-watch-import.yml`
- Create: `.github/workflows/polaris-watch-breakdown-strategy-gap.yml`
- Create: `.github/workflows/polaris-watch-bad-actor-watchlist.yml`
- Create: `.github/workflows/polaris-watch-maintenance-strategy-health-check.yml`

- [ ] **Step 1: Add import workflow**

Create `.github/workflows/polaris-watch-import.yml`:

```yaml
name: Polaris Watch Import

on:
  schedule:
    - cron: "5 14 * * *"
  workflow_dispatch:

jobs:
  import:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/api
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -r requirements.txt
      - run: python -m alembic upgrade head
      - run: >
          python -m app.cli.import_daily_reliability_data
          --work-orders-csv sample_data/reliability/work_orders.csv
          --work-order-failure-modes-csv sample_data/reliability/work_order_failure_modes.csv
```

- [ ] **Step 2: Add breakdown strategy gap workflow**

Create `.github/workflows/polaris-watch-breakdown-strategy-gap.yml`:

```yaml
name: Polaris Watch Breakdown Strategy Gap

on:
  schedule:
    - cron: "20 14 * * *"
  workflow_dispatch:

jobs:
  review:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/api
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL: ${{ secrets.SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL }}
      SCHEDULED_REVIEW_TEAMS_DESTINATION_LABEL: Reliability Team
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -r requirements.txt
      - run: python -m alembic upgrade head
      - run: >
          python -m app.cli.run_scheduled_review
          --template breakdown_strategy_gap
          --lookback-days 1
```

- [ ] **Step 3: Add bad actor watchlist workflow**

Create `.github/workflows/polaris-watch-bad-actor-watchlist.yml`:

```yaml
name: Polaris Watch Bad Actor Watchlist

on:
  schedule:
    - cron: "30 14 * * *"
  workflow_dispatch:

jobs:
  review:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/api
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL: ${{ secrets.SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL }}
      SCHEDULED_REVIEW_TEAMS_DESTINATION_LABEL: Reliability Team
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -r requirements.txt
      - run: python -m alembic upgrade head
      - run: >
          python -m app.cli.run_scheduled_review
          --template bad_actor_watchlist
          --lookback-days 30
```

- [ ] **Step 4: Add maintenance strategy health check workflow**

Create `.github/workflows/polaris-watch-maintenance-strategy-health-check.yml`:

```yaml
name: Polaris Watch Maintenance Strategy Health Check

on:
  schedule:
    - cron: "40 14 * * *"
  workflow_dispatch:

jobs:
  review:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/api
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL: ${{ secrets.SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL }}
      SCHEDULED_REVIEW_TEAMS_DESTINATION_LABEL: Reliability Team
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -r requirements.txt
      - run: python -m alembic upgrade head
      - run: >
          python -m app.cli.run_scheduled_review
          --template maintenance_strategy_health_check
          --lookback-days 30
```

- [ ] **Step 5: Validate workflow YAML files are present**

Run:

```bash
ls .github/workflows/polaris-watch-*.yml
```

Expected: four Polaris Watch workflow files are listed.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/polaris-watch-*.yml
git commit -m "Add Polaris Watch GitHub Actions schedules"
```

## Task 9: Final Verification and Milestone Update

**Files:**
- Modify: `milestones.md` if available in the working tree
- Use: all files from prior tasks

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
cd apps/api
python -m pytest \
  tests/test_scheduled_review_models.py \
  tests/test_config.py \
  tests/test_daily_reliability_import_service.py \
  tests/test_scheduled_review_report_builder.py \
  tests/test_scheduled_review_service.py \
  tests/test_notification_delivery.py \
  tests/test_run_scheduled_review_cli.py \
  -v
```

Expected: PASS.

- [ ] **Step 2: Run broader backend tests that cover reused agents**

Run:

```bash
cd apps/api
python -m pytest \
  tests/test_defect_elimination_agent.py \
  tests/test_maintenance_strategy_agent.py \
  tests/test_reliability_seed_loader.py \
  -v
```

Expected: PASS.

- [ ] **Step 3: Run Alembic upgrade check**

Run:

```bash
cd apps/api
.venv/bin/alembic upgrade head
```

Expected: migration completes without errors in the configured local database.

- [ ] **Step 4: Update milestone text locally**

If `milestones.md` exists, ensure it contains:

```markdown
| Polaris Watch | Next | Add GitHub Actions cron workflows for daily work-order and work-order failure-mode import, plus three predefined daily review templates that send separate Microsoft Teams reports: breakdown strategy gaps, bad actor watchlist, and maintenance strategy health check. |
```

If `milestones.md` is ignored by git, leave it as a local progress-tracking file and do not force-add it unless the user explicitly asks.

- [ ] **Step 5: Commit final adjustments**

If any tracked files changed during verification:

```bash
git add <changed tracked files>
git commit -m "Verify Polaris Watch implementation"
```

If only ignored local files changed, do not create an empty commit.
