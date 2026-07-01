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

    def scalar(self, _statement: Any) -> Any:
        if self.scalar_results:
            return self.scalar_results.pop(0)
        return None

    def commit(self) -> None:
        self.commit_count += 1


def test_daily_import_upserts_work_orders_and_failure_mode_links(
    tmp_path: Path,
) -> None:
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
        "Seal leak,2026-06-29T00:00:00+00:00,,,,"
        "1000,2\n",
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
        DailyReliabilityImportService(session).import_files(
            work_orders_csv,
            links_csv,
        )
