import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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


ALLOWED_MAINTENANCE_ACTIVITY_TYPES = {
    "corrective",
    "preventive",
    "emergency",
    "inspection",
    "condition_monitoring",
    "other",
    "unknown",
}
ALLOWED_LINK_SOURCES = {"user", "rule", "agent", "import"}
WORK_ORDER_REQUIRED_HEADERS = {"order_number"}
LINK_REQUIRED_HEADERS = {"order_number", "failure_mode_name"}


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
        work_order_rows = _read_csv(work_orders_csv, WORK_ORDER_REQUIRED_HEADERS)
        link_rows = _read_csv(work_order_failure_modes_csv, LINK_REQUIRED_HEADERS)
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
            work_order_count=len(work_orders_by_number),
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
            work_order = work_orders_by_number.get(order_number)
            if work_order is None:
                work_order = self.session.scalar(
                    select(WorkOrder).where(WorkOrder.order_number == order_number)
                )
                if work_order is None:
                    work_order = WorkOrder(order_number=order_number)
                    self.session.add(work_order)
                work_orders_by_number[order_number] = work_order

            equipment = _resolve_equipment(self.session, row)
            maintenance_activity_type = _optional(
                row,
                "maintenance_activity_type",
            ) or "unknown"
            if maintenance_activity_type not in ALLOWED_MAINTENANCE_ACTIVITY_TYPES:
                raise DailyReliabilityImportError(
                    "Invalid maintenance_activity_type "
                    f"{maintenance_activity_type!r}; expected one of "
                    f"{sorted(ALLOWED_MAINTENANCE_ACTIVITY_TYPES)}"
                )
            work_order.notification_number = _optional(row, "notification_number")
            work_order.equipment = equipment
            work_order.functional_location = _optional(row, "functional_location")
            work_order.order_type = _optional(row, "order_type")
            work_order.status = _optional(row, "status")
            work_order.priority = _optional(row, "priority")
            work_order.maintenance_activity_type = maintenance_activity_type
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
        return work_orders_by_number

    def _upsert_links(
        self,
        rows: list[dict[str, str]],
        work_orders_by_number: dict[str, WorkOrder],
    ) -> int:
        links_by_key: dict[tuple[str, str, str | None], WorkOrderFailureMode] = {}
        for row in rows:
            order_number = _required(row, "order_number")
            work_order = work_orders_by_number.get(order_number)
            if work_order is None:
                raise DailyReliabilityImportError(
                    f"Unknown work order in failure-mode link: {order_number}"
                )
            failure_mode = _resolve_failure_mode(self.session, row)
            link_key = (
                order_number,
                failure_mode.name,
                failure_mode.equipment_type,
            )
            existing_link = links_by_key.get(link_key)
            if existing_link is None:
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
                links_by_key[link_key] = existing_link
            existing_link.source = _parse_source(_optional(row, "source"))
            existing_link.confidence = _parse_confidence(
                _optional(row, "confidence")
            )
            existing_link.evidence = _optional(row, "evidence")
        return len(links_by_key)


def _read_csv(
    path: Path,
    required_headers: set[str],
) -> list[dict[str, str]]:
    if not path.exists():
        raise DailyReliabilityImportError(f"CSV file does not exist: {path}")

    try:
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file, strict=True)
            if reader.fieldnames is None:
                raise DailyReliabilityImportError(
                    f"CSV file has no header row: {path}"
                )
            fieldnames = set(reader.fieldnames)
            missing_headers = sorted(required_headers - fieldnames)
            if missing_headers:
                raise DailyReliabilityImportError(
                    f"Missing required headers in {path}: "
                    f"{', '.join(missing_headers)}"
                )
            rows = []
            for line_number, row in enumerate(reader, start=2):
                if None in row:
                    raise DailyReliabilityImportError(
                        f"Malformed CSV row in {path} at line {line_number}: "
                        "too many columns"
                    )
                rows.append(
                    {
                        key: value.strip() if value is not None else ""
                        for key, value in row.items()
                    }
                )
            return rows
    except DailyReliabilityImportError:
        raise
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise DailyReliabilityImportError(
            f"Unable to read CSV file {path}: {exc}"
        ) from exc


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
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise DailyReliabilityImportError(
            f"Invalid datetime value: {value}"
        ) from exc


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DailyReliabilityImportError(
            f"Invalid decimal value: {value}"
        ) from exc
    if not parsed.is_finite():
        raise DailyReliabilityImportError(
            f"Invalid decimal value: {value}; expected a finite number"
        )
    return parsed


def _parse_confidence(value: str | None) -> Decimal | None:
    confidence = _parse_decimal(value)
    if confidence is None:
        return None
    if confidence < 0 or confidence > 1:
        raise DailyReliabilityImportError(
            f"Invalid confidence value: {confidence}; expected 0..1"
        )
    return confidence


def _parse_source(value: str | None) -> str:
    source = value or "import"
    if source not in ALLOWED_LINK_SOURCES:
        raise DailyReliabilityImportError(
            f"Invalid source {source!r}; expected one of {sorted(ALLOWED_LINK_SOURCES)}"
        )
    return source
