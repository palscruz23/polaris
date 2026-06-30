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
        if hasattr(self.session, "flush"):
            self.session.flush()
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
            work_order.downtime_hours = _parse_decimal(_optional(row, "downtime_hours"))
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
            existing_link = self.session.scalar(
                select(WorkOrderFailureMode).where(
                    WorkOrderFailureMode.work_order == work_order,
                    WorkOrderFailureMode.failure_mode == failure_mode,
                )
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
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise DailyReliabilityImportError(f"CSV file has no header row: {path}")
        return [
            {
                key: value.strip() if value is not None else ""
                for key, value in row.items()
            }
            for row in reader
        ]


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
