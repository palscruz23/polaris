from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import ColumnElement, FromClause, Table, Text, cast, func, select
from sqlalchemy.orm import Session

from app import models as _models  # noqa: F401
from app.database import Base, get_database_session
from app.schemas.data_browser import (
    DataTablePageResponse,
    DataTableSummaryResponse,
)

router = APIRouter(
    prefix="/data",
    tags=["data"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]

USER_VISIBLE_TABLES = (
    "equipment",
    "failure_modes",
    "maintenance_strategies",
    "work_order_failure_modes",
    "work_orders",
)

ColumnLookup = dict[str, ColumnElement[Any]]


@router.get(
    "/tables",
    response_model=list[DataTableSummaryResponse],
)
def list_data_tables(
    session: DatabaseSession,
) -> list[DataTableSummaryResponse]:
    return [
        DataTableSummaryResponse(
            name=table.name,
            columns=_display_columns_for_table(table),
            row_count=_row_count(session, table),
        )
        for table in _tables()
    ]


@router.get(
    "/tables/{table_name}",
    response_model=DataTablePageResponse,
)
def get_data_table(
    table_name: str,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    filter: Annotated[list[str] | None, Query()] = None,
) -> DataTablePageResponse:
    table = _table_by_name(table_name)

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data table not found.",
        )

    row_source = _row_source_for_table(table)
    columns = _column_lookup_for_table(table)
    filters = _column_filters(columns, filter or [])
    row_count = _row_count(session, row_source, filters)
    rows = [
        {
            column_name: _serialize_value(row[column_name])
            for column_name in columns
        }
        for row in session.execute(
            select(*columns.values())
            .select_from(row_source)
            .where(*filters)
            .limit(limit)
            .offset(offset)
        ).mappings()
    ]

    return DataTablePageResponse(
        name=table.name,
        columns=list(columns),
        rows=rows,
        row_count=row_count,
        limit=limit,
        offset=offset,
        has_more=offset + len(rows) < row_count,
    )


def _tables() -> list[Table]:
    return [
        table
        for table_name in USER_VISIBLE_TABLES
        if (table := Base.metadata.tables.get(table_name)) is not None
    ]


def _table_by_name(table_name: str) -> Table | None:
    if table_name not in USER_VISIBLE_TABLES:
        return None

    return Base.metadata.tables.get(table_name)


def _display_columns_for_table(table: Table) -> list[str]:
    return list(_column_lookup_for_table(table))


def _column_lookup_for_table(table: Table) -> ColumnLookup:
    if table.name == "maintenance_strategies":
        return _maintenance_strategy_columns(table)

    if table.name != "work_order_failure_modes":
        return _move_id_column_to_end(
            {column.name: column for column in table.columns}
        )

    work_orders = Base.metadata.tables["work_orders"]
    failure_modes = Base.metadata.tables["failure_modes"]

    return {
        "work_order_number": work_orders.c.order_number.label("work_order_number"),
        "short_text": work_orders.c.short_text.label("short_text"),
        "failure_mode": failure_modes.c.name.label("failure_mode"),
        "work_order_id": table.c.work_order_id,
        "failure_mode_id": table.c.failure_mode_id,
        "source": table.c.source,
        "confidence": table.c.confidence,
        "evidence": table.c.evidence,
        "created_at": table.c.created_at,
        "id": table.c.id,
    }


def _maintenance_strategy_columns(table: Table) -> ColumnLookup:
    equipment = Base.metadata.tables["equipment"]

    return {
        "strategy_number": table.c.strategy_number,
        "task_number": table.c.task_number,
        "equipment_number": equipment.c.equipment_number.label("equipment_number"),
        "functional_location": func.coalesce(
            table.c.functional_location,
            equipment.c.functional_location,
        ).label("functional_location"),
        "task_description": table.c.task_description,
        "strategy_type": table.c.strategy_type,
        "frequency_value": table.c.frequency_value,
        "frequency_unit": table.c.frequency_unit,
        "status": table.c.status,
        "equipment_id": table.c.equipment_id,
        "import_batch_id": table.c.import_batch_id,
        "created_at": table.c.created_at,
        "updated_at": table.c.updated_at,
        "id": table.c.id,
    }


def _move_id_column_to_end(columns: ColumnLookup) -> ColumnLookup:
    if "id" not in columns:
        return columns

    id_column = columns["id"]
    return {
        **{
            column_name: column
            for column_name, column in columns.items()
            if column_name != "id"
        },
        "id": id_column,
    }


def _row_source_for_table(table: Table) -> FromClause:
    if table.name == "maintenance_strategies":
        equipment = Base.metadata.tables["equipment"]

        return table.outerjoin(
            equipment,
            table.c.equipment_id == equipment.c.id,
        )

    if table.name != "work_order_failure_modes":
        return table

    work_orders = Base.metadata.tables["work_orders"]
    failure_modes = Base.metadata.tables["failure_modes"]

    return table.join(
        work_orders,
        table.c.work_order_id == work_orders.c.id,
    ).join(
        failure_modes,
        table.c.failure_mode_id == failure_modes.c.id,
    )


def _row_count(
    session: Session,
    row_source: FromClause,
    filters: list[object] | None = None,
) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(row_source).where(*(filters or []))
        )
        or 0
    )


def _column_filters(
    columns: Table | ColumnLookup,
    raw_filters: list[str],
) -> list[object]:
    filters: list[object] = []

    for raw_filter in raw_filters:
        column_name, separator, value = raw_filter.partition("=")
        value = value.strip()

        if not separator or not column_name or not value:
            continue

        if isinstance(columns, Table):
            column = columns.columns.get(column_name)
        else:
            column = columns.get(column_name)

        if column is None:
            continue

        filters.append(
            cast(column, Text).ilike(f"%{value}%")
        )

    return filters


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, UUID):
        return str(value)

    return value
