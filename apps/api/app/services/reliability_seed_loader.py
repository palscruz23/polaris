import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Equipment,
    FailureMode,
    ImportBatch,
    MaintenanceStrategy,
    WorkOrder,
    WorkOrderFailureMode,
)


class SeedLoadError(Exception):
    """Raised when clean reliability seed data cannot be loaded."""


@dataclass(frozen=True)
class SeedLoadSummary:
    equipment_count: int
    failure_mode_count: int
    maintenance_strategy_count: int
    work_order_count: int
    work_order_failure_mode_count: int


def load_clean_reliability_seed_data(
    session: Session,
    seed_directory: Path,
) -> SeedLoadSummary:
    loader = ReliabilitySeedLoader(session)

    return loader.load(seed_directory)


class ReliabilitySeedLoader:
    def __init__(self, session: Session):
        self.session = session

    def load(self, seed_directory: Path) -> SeedLoadSummary:
        if not seed_directory.exists() or not seed_directory.is_dir():
            raise SeedLoadError(f"Seed directory does not exist: {seed_directory}")

        equipment_rows = _read_csv(seed_directory / "equipment.csv")
        failure_mode_rows = _read_csv(seed_directory / "failure_modes.csv")
        strategy_rows = _read_csv(seed_directory / "maintenance_strategies.csv")
        work_order_rows = _read_csv(seed_directory / "work_orders.csv")
        failure_link_rows = _read_optional_csv(
            seed_directory / "work_order_failure_modes.csv"
        )

        equipment_batch = self._create_batch(
            seed_directory,
            "equipment",
            len(equipment_rows),
        )
        failure_mode_batch = self._create_batch(
            seed_directory,
            "failure_modes",
            len(failure_mode_rows),
        )
        strategy_batch = self._create_batch(
            seed_directory,
            "maintenance_strategies",
            len(strategy_rows),
        )
        work_order_batch = self._create_batch(
            seed_directory,
            "work_orders",
            len(work_order_rows),
        )

        equipment_by_number = self._load_equipment(
            equipment_rows,
            equipment_batch,
        )
        failure_modes_by_key = self._load_failure_modes(
            failure_mode_rows,
            failure_mode_batch,
        )
        strategy_count = self._load_maintenance_strategies(
            strategy_rows,
            strategy_batch,
            equipment_by_number,
        )
        work_orders_by_number = self._load_work_orders(
            work_order_rows,
            work_order_batch,
            equipment_by_number,
        )
        failure_link_count = self._load_work_order_failure_modes(
            failure_link_rows,
            work_orders_by_number,
            failure_modes_by_key,
        )

        self.session.commit()

        return SeedLoadSummary(
            equipment_count=len(equipment_rows),
            failure_mode_count=len(failure_mode_rows),
            maintenance_strategy_count=strategy_count,
            work_order_count=len(work_order_rows),
            work_order_failure_mode_count=failure_link_count,
        )

    def _create_batch(
        self,
        seed_directory: Path,
        dataset_type: str,
        record_count: int,
    ) -> ImportBatch:
        batch = ImportBatch(
            source_name=str(seed_directory),
            dataset_type=dataset_type,
            status="completed",
            record_count=record_count,
            completed_at=datetime.now(UTC),
        )
        self.session.add(batch)

        return batch

    def _load_equipment(
        self,
        rows: list[dict[str, str]],
        import_batch: ImportBatch,
    ) -> dict[str, Equipment]:
        equipment_by_number: dict[str, Equipment] = {}

        for row in rows:
            equipment_number = _required(row, "equipment_number")
            equipment = self.session.scalar(
                select(Equipment).where(
                    Equipment.equipment_number == equipment_number
                )
            )

            if equipment is None:
                equipment = Equipment(equipment_number=equipment_number)
                self.session.add(equipment)

            equipment.functional_location = _optional(row, "functional_location")
            equipment.description = _optional(row, "description")
            equipment.parent_functional_location = _optional(
                row,
                "parent_functional_location",
            )
            equipment.equipment_type = _optional(row, "equipment_type")
            equipment.system = _optional(row, "system")
            equipment.criticality = _optional(row, "criticality")
            equipment.status = _optional(row, "status") or "unknown"
            equipment.install_date = _parse_date(_optional(row, "install_date"))
            equipment.import_batch = import_batch
            equipment_by_number[equipment_number] = equipment

        return equipment_by_number

    def _load_failure_modes(
        self,
        rows: list[dict[str, str]],
        import_batch: ImportBatch,
    ) -> dict[tuple[str, str | None], FailureMode]:
        failure_modes_by_key: dict[tuple[str, str | None], FailureMode] = {}

        for row in rows:
            name = _required(row, "name")
            equipment_type = _optional(row, "equipment_type")
            failure_mode = self.session.scalar(
                select(FailureMode).where(
                    FailureMode.name == name,
                    FailureMode.equipment_type == equipment_type,
                )
            )

            if failure_mode is None:
                failure_mode = FailureMode(
                    name=name,
                    equipment_type=equipment_type,
                )
                self.session.add(failure_mode)

            failure_mode.mechanism = _optional(row, "mechanism")
            failure_mode.cause = _optional(row, "cause")
            failure_mode.symptom = _optional(row, "symptom")
            failure_mode.consequence_category = _optional(
                row,
                "consequence_category",
            )
            failure_mode.import_batch = import_batch
            failure_modes_by_key[(name, equipment_type)] = failure_mode

        return failure_modes_by_key

    def _load_maintenance_strategies(
        self,
        rows: list[dict[str, str]],
        import_batch: ImportBatch,
        equipment_by_number: dict[str, Equipment],
    ) -> int:
        for row in rows:
            task_number = _optional(row, "task_number")
            strategy_number = _optional(row, "strategy_number")
            equipment = _resolve_equipment(row, equipment_by_number)
            functional_location = _optional(row, "functional_location")
            if functional_location is None and equipment is not None:
                functional_location = equipment.functional_location

            if equipment is None and functional_location is None:
                raise SeedLoadError(
                    "Maintenance strategy rows require equipment_number or "
                    "functional_location."
                )

            strategy = self.session.scalar(
                select(MaintenanceStrategy).where(
                    MaintenanceStrategy.strategy_number == strategy_number,
                    MaintenanceStrategy.task_number == task_number,
                )
            )

            if strategy is None:
                strategy = MaintenanceStrategy(
                    strategy_number=strategy_number,
                    task_number=task_number,
                    task_description=_required(row, "task_description"),
                )
                self.session.add(strategy)

            strategy.equipment = equipment
            strategy.functional_location = functional_location
            strategy.task_description = _required(row, "task_description")
            strategy.strategy_type = _optional(row, "strategy_type") or "other"
            strategy.frequency_value = _parse_decimal(
                _optional(row, "frequency_value")
            )
            strategy.frequency_unit = _optional(row, "frequency_unit")
            strategy.status = _optional(row, "status") or "active"
            strategy.import_batch = import_batch

        return len(rows)

    def _load_work_orders(
        self,
        rows: list[dict[str, str]],
        import_batch: ImportBatch,
        equipment_by_number: dict[str, Equipment],
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

            work_order.notification_number = _optional(
                row,
                "notification_number",
            )
            work_order.equipment = _resolve_equipment(row, equipment_by_number)
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
            work_order.import_batch = import_batch
            work_orders_by_number[order_number] = work_order

        return work_orders_by_number

    def _load_work_order_failure_modes(
        self,
        rows: list[dict[str, str]],
        work_orders_by_number: dict[str, WorkOrder],
        failure_modes_by_key: dict[tuple[str, str | None], FailureMode],
    ) -> int:
        for row in rows:
            order_number = _required(row, "order_number")
            failure_mode_name = _required(row, "failure_mode_name")
            equipment_type = _optional(row, "equipment_type")

            work_order = work_orders_by_number.get(order_number)
            if work_order is None:
                raise SeedLoadError(f"Unknown work order: {order_number}")

            failure_mode = failure_modes_by_key.get(
                (failure_mode_name, equipment_type)
            )
            if failure_mode is None:
                raise SeedLoadError(
                    f"Unknown failure mode: {failure_mode_name}"
                )

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

        return len(rows)


def _read_optional_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    return _read_csv(path)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SeedLoadError(f"Required seed file is missing: {path.name}")

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise SeedLoadError(f"Seed file has no header row: {path.name}")

        return [
            {
                key: value.strip() if value is not None else ""
                for key, value in row.items()
            }
            for row in reader
        ]


def _required(row: dict[str, str], column_name: str) -> str:
    value = _optional(row, column_name)
    if value is None:
        raise SeedLoadError(f"Required column is missing or blank: {column_name}")

    return value


def _optional(row: dict[str, str], column_name: str) -> str | None:
    value = row.get(column_name, "").strip()

    return value or None


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None

    return date.fromisoformat(value)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None

    return Decimal(value)


def _resolve_equipment(
    row: dict[str, str],
    equipment_by_number: dict[str, Equipment],
) -> Equipment | None:
    equipment_number = _optional(row, "equipment_number")
    if equipment_number is None:
        return None

    equipment = equipment_by_number.get(equipment_number)
    if equipment is None:
        raise SeedLoadError(f"Unknown equipment number: {equipment_number}")

    return equipment
