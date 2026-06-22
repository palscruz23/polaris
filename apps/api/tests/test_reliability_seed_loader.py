import csv
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from app.models import (
    Equipment,
    FailureMode,
    ImportBatch,
    MaintenanceStrategy,
    WorkOrder,
    WorkOrderFailureMode,
)
from app.services.reliability_seed_loader import (
    SeedLoadError,
    load_clean_reliability_seed_data,
)


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commit_count = 0

    def add(self, item: Any) -> None:
        self.added.append(item)

    def scalar(self, _statement: Any) -> None:
        return None

    def commit(self) -> None:
        self.commit_count += 1


def test_clean_reliability_seed_loader_loads_sample_data() -> None:
    session = FakeSession()
    seed_directory = Path("sample_data/reliability")

    summary = load_clean_reliability_seed_data(session, seed_directory)

    assert summary.equipment_count == 50
    assert summary.failure_mode_count == 21
    assert summary.maintenance_strategy_count == 100
    assert summary.work_order_count == 1000
    assert summary.work_order_failure_mode_count == 653
    assert session.commit_count == 1
    assert _count_added(session, ImportBatch) == 4
    assert _count_added(session, Equipment) == 50
    assert _count_added(session, FailureMode) == 21
    assert _count_added(session, MaintenanceStrategy) == 100
    assert _count_added(session, WorkOrder) == 1000
    assert _count_added(session, WorkOrderFailureMode) == 653


def test_sample_work_orders_cover_three_calendar_years() -> None:
    with Path("sample_data/reliability/work_orders.csv").open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    created_years = {
        datetime.fromisoformat(row["created_at_source"]).year for row in rows
    }

    assert len(rows) == 1000
    assert created_years == {2023, 2024, 2025}


def test_clean_reliability_seed_loader_requires_known_equipment(
    tmp_path: Path,
) -> None:
    _write_required_seed_files(
        tmp_path,
        work_orders=(
            "order_number,notification_number,equipment_number,functional_location,"
            "order_type,status,priority,maintenance_activity_type,short_text,"
            "long_text,created_at_source,required_by_at,started_at,finished_at,"
            "total_cost,downtime_hours\n"
            "WO-1,,UNKNOWN,,CM,closed,high,corrective,Repair pump,,,,,,,\n"
        ),
    )

    with pytest.raises(SeedLoadError, match="Unknown equipment number"):
        load_clean_reliability_seed_data(FakeSession(), tmp_path)


def _count_added(session: FakeSession, model_type: type) -> int:
    return sum(isinstance(item, model_type) for item in session.added)


def _write_required_seed_files(
    directory: Path,
    work_orders: str,
) -> None:
    (directory / "equipment.csv").write_text(
        "equipment_number,functional_location,description,"
        "parent_equipment_number,parent_functional_location,equipment_type,"
        "system,criticality,status,install_date\n"
        "P-101,PLANT/PUMP,Primary pump,,,pump,cooling,A,active,2020-01-01\n",
        encoding="utf-8",
    )
    (directory / "failure_modes.csv").write_text(
        "name,equipment_type,mechanism,cause,symptom,consequence_category\n"
        "Bearing failure,pump,fatigue,poor lubrication,vibration,production\n",
        encoding="utf-8",
    )
    (directory / "maintenance_strategies.csv").write_text(
        "strategy_number,task_number,equipment_number,functional_location,"
        "task_description,strategy_type,frequency_value,frequency_unit,status\n"
        "PM-1,T-1,P-101,,Inspect pump,inspection,4,weeks,active\n",
        encoding="utf-8",
    )
    (directory / "work_orders.csv").write_text(work_orders, encoding="utf-8")
