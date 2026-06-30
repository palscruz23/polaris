from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import (
    Equipment,
    FailureMode,
    ImportBatch,
    WorkOrder,
    WorkOrderFailureMode,
)
from app.services.daily_reliability_import_service import (
    DailyReliabilityImportError,
    DailyReliabilityImportService,
)


WORK_ORDER_HEADER = (
    "order_number,notification_number,equipment_number,functional_location,"
    "order_type,status,priority,maintenance_activity_type,short_text,"
    "long_text,created_at_source,required_by_at,started_at,finished_at,"
    "total_cost,downtime_hours\n"
)
LINK_HEADER = (
    "order_number,failure_mode_name,equipment_type,source,confidence,evidence\n"
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
        "Seal leak,2026-06-29T00:00:00+00:00,,,2026-06-29T02:00:00+00:00,1000,2\n",
        encoding="utf-8",
    )
    links_csv.write_text(
        "order_number,failure_mode_name,equipment_type,source,confidence,evidence\n"
        "WO-1,Seal leakage,pump,import,0.900,WO text mentions seal leak\n",
        encoding="utf-8",
    )
    session.scalar_results = [None, equipment, failure_mode, None]

    summary = DailyReliabilityImportService(session).import_files(
        work_orders_csv,
        links_csv,
    )

    assert summary.work_order_count == 1
    assert summary.work_order_failure_mode_count == 1
    assert session.commit_count == 1
    assert session.scalar_results == []
    import_batch = next(item for item in session.added if isinstance(item, ImportBatch))
    assert import_batch.dataset_type == "work_orders"
    assert import_batch.status == "completed"
    assert import_batch.record_count == 1
    work_order = next(item for item in session.items if isinstance(item, WorkOrder))
    assert work_order.order_number == "WO-1"
    assert work_order.equipment is equipment
    assert work_order.status == "closed"
    assert work_order.short_text == "Repair seal"
    assert work_order.total_cost == Decimal("1000")
    link = next(
        item for item in session.added if isinstance(item, WorkOrderFailureMode)
    )
    assert link.work_order is work_order
    assert link.failure_mode is failure_mode
    assert link.source == "import"
    assert link.confidence == Decimal("0.900")
    assert link.evidence == "WO text mentions seal leak"


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


def test_daily_import_is_idempotent_for_duplicate_rows_in_one_batch(
    tmp_path: Path,
) -> None:
    session = _sqlite_session(tmp_path)
    equipment = Equipment(equipment_number="P-101", equipment_type="pump")
    failure_mode = FailureMode(name="Seal leakage", equipment_type="pump")
    session.add_all([equipment, failure_mode])
    session.commit()
    work_orders_csv = tmp_path / "work_orders.csv"
    links_csv = tmp_path / "work_order_failure_modes.csv"
    work_orders_csv.write_text(
        WORK_ORDER_HEADER +
        "WO-1,,P-101,PLANT/PUMP,CM,open,high,corrective,Initial seal repair,"
        ",2026-06-29T00:00:00+00:00,,,,100,1\n"
        "WO-1,,P-101,PLANT/PUMP,CM,closed,high,corrective,Updated seal repair,"
        ",2026-06-29T00:00:00+00:00,,,,125,2\n",
        encoding="utf-8",
    )
    links_csv.write_text(
        LINK_HEADER +
        "WO-1,Seal leakage,pump,rule,0.500,Initial evidence\n"
        "WO-1,Seal leakage,pump,import,0.900,Updated evidence\n",
        encoding="utf-8",
    )

    summary = DailyReliabilityImportService(session).import_files(
        work_orders_csv,
        links_csv,
    )

    work_orders = session.scalars(select(WorkOrder)).all()
    links = session.scalars(select(WorkOrderFailureMode)).all()
    assert summary.work_order_count == 1
    assert summary.work_order_failure_mode_count == 1
    assert len(work_orders) == 1
    assert work_orders[0].status == "closed"
    assert work_orders[0].short_text == "Updated seal repair"
    assert work_orders[0].total_cost == Decimal("125.00")
    assert len(links) == 1
    assert links[0].source == "import"
    assert links[0].confidence == Decimal("0.900")
    assert links[0].evidence == "Updated evidence"


@pytest.mark.parametrize(
    ("created_at_source", "total_cost", "error_match"),
    [
        ("not-a-date", "100", "Invalid datetime"),
        ("2026-06-29T00:00:00+00:00", "not-a-decimal", "Invalid decimal"),
    ],
)
def test_daily_import_rejects_invalid_datetime_or_decimal(
    tmp_path: Path,
    created_at_source: str,
    total_cost: str,
    error_match: str,
) -> None:
    session = _sqlite_session(tmp_path)
    session.add(Equipment(equipment_number="P-101", equipment_type="pump"))
    session.commit()
    work_orders_csv = tmp_path / "work_orders.csv"
    links_csv = tmp_path / "work_order_failure_modes.csv"
    work_orders_csv.write_text(
        WORK_ORDER_HEADER +
        "WO-1,,P-101,PLANT/PUMP,CM,open,high,corrective,Repair seal,"
        f",{created_at_source},,,,{total_cost},1\n",
        encoding="utf-8",
    )
    links_csv.write_text(LINK_HEADER, encoding="utf-8")

    with pytest.raises(DailyReliabilityImportError, match=error_match):
        DailyReliabilityImportService(session).import_files(work_orders_csv, links_csv)


def test_daily_import_rejects_missing_required_headers(tmp_path: Path) -> None:
    session = _sqlite_session(tmp_path)
    work_orders_csv = tmp_path / "work_orders.csv"
    links_csv = tmp_path / "work_order_failure_modes.csv"
    work_orders_csv.write_text(
        "notification_number,equipment_number\n"
        "N-1,P-101\n",
        encoding="utf-8",
    )
    links_csv.write_text(LINK_HEADER, encoding="utf-8")

    with pytest.raises(DailyReliabilityImportError, match="Missing required headers"):
        DailyReliabilityImportService(session).import_files(work_orders_csv, links_csv)


def test_daily_import_rejects_malformed_rows_with_extra_columns(
    tmp_path: Path,
) -> None:
    session = _sqlite_session(tmp_path)
    work_orders_csv = tmp_path / "work_orders.csv"
    links_csv = tmp_path / "work_order_failure_modes.csv"
    work_orders_csv.write_text(
        WORK_ORDER_HEADER +
        "WO-1,,P-101,PLANT/PUMP,CM,open,high,corrective,Repair seal,"
        ",2026-06-29T00:00:00+00:00,,,,100,1,unexpected\n",
        encoding="utf-8",
    )
    links_csv.write_text(LINK_HEADER, encoding="utf-8")

    with pytest.raises(DailyReliabilityImportError, match="too many columns"):
        DailyReliabilityImportService(session).import_files(work_orders_csv, links_csv)


def test_daily_import_wraps_invalid_utf8_as_import_error(tmp_path: Path) -> None:
    session = _sqlite_session(tmp_path)
    work_orders_csv = tmp_path / "work_orders.csv"
    links_csv = tmp_path / "work_order_failure_modes.csv"
    work_orders_csv.write_bytes(b"\xff\xfe\xfa")
    links_csv.write_text(LINK_HEADER, encoding="utf-8")

    with pytest.raises(DailyReliabilityImportError) as exc_info:
        DailyReliabilityImportService(session).import_files(work_orders_csv, links_csv)

    assert str(work_orders_csv) in str(exc_info.value)
    assert "Unable to read CSV file" in str(exc_info.value)


@pytest.mark.parametrize(
    ("maintenance_activity_type", "source", "confidence", "error_match"),
    [
        ("invalid_activity", "import", "0.900", "Invalid maintenance_activity_type"),
        ("corrective", "spreadsheet", "0.900", "Invalid source"),
        ("corrective", "import", "1.100", "Invalid confidence"),
        ("corrective", "import", "NaN", "Invalid decimal"),
    ],
)
def test_daily_import_rejects_values_that_violate_model_constraints(
    tmp_path: Path,
    maintenance_activity_type: str,
    source: str,
    confidence: str,
    error_match: str,
) -> None:
    session = _sqlite_session(tmp_path)
    session.add_all(
        [
            Equipment(equipment_number="P-101", equipment_type="pump"),
            FailureMode(name="Seal leakage", equipment_type="pump"),
        ]
    )
    session.commit()
    work_orders_csv = tmp_path / "work_orders.csv"
    links_csv = tmp_path / "work_order_failure_modes.csv"
    work_orders_csv.write_text(
        WORK_ORDER_HEADER +
        f"WO-1,,P-101,PLANT/PUMP,CM,open,high,{maintenance_activity_type},"
        "Repair seal,,2026-06-29T00:00:00+00:00,,,,100,1\n",
        encoding="utf-8",
    )
    links_csv.write_text(
        LINK_HEADER +
        f"WO-1,Seal leakage,pump,{source},{confidence},Evidence\n",
        encoding="utf-8",
    )

    with pytest.raises(DailyReliabilityImportError, match=error_match):
        DailyReliabilityImportService(session).import_files(work_orders_csv, links_csv)


def _sqlite_session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'daily-import.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    return session_factory()
