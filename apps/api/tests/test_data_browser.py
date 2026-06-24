from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Column, MetaData, Table, Text

from app.routes import data_browser


class FakeSession:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def execute(self, _statement: object) -> "FakeExecuteResult":
        return FakeExecuteResult(self.rows)


class FakeExecuteResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def mappings(self) -> list[dict[str, Any]]:
        return self.rows


def test_data_table_page_serializes_values_and_pagination(monkeypatch: object) -> None:
    table = Table(
        "sample_table",
        MetaData(),
        Column("id", Text),
        Column("amount", Text),
        Column("created_at", Text),
    )

    monkeypatch.setattr(  # type: ignore[attr-defined]
        data_browser,
        "_table_by_name",
        lambda _name: table,
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        data_browser,
        "_row_count",
        lambda _session, _table, _filters=None: 3,
    )

    page = data_browser.get_data_table(
        "sample_table",
        FakeSession(  # type: ignore[arg-type]
            [
                {
                    "id": UUID("00000000-0000-0000-0000-000000000001"),
                    "amount": Decimal("12.50"),
                    "created_at": datetime(2026, 1, 2, 3, 4, 5),
                }
            ]
        ),
        limit=1,
        offset=1,
        filter=["amount=12"],
    )

    assert page.name == "sample_table"
    assert page.columns == ["amount", "created_at", "id"]
    assert page.rows == [
        {
            "amount": "12.50",
            "created_at": "2026-01-02T03:04:05",
            "id": "00000000-0000-0000-0000-000000000001",
        }
    ]
    assert page.has_more is True


def test_data_table_page_returns_404_for_unknown_table(monkeypatch: object) -> None:
    monkeypatch.setattr(  # type: ignore[attr-defined]
        data_browser,
        "_table_by_name",
        lambda _name: None,
    )

    try:
        data_browser.get_data_table(
            "missing",
            FakeSession([]),  # type: ignore[arg-type]
        )
    except HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError("Expected HTTPException for missing table.")


def test_data_browser_exposes_user_visible_reliability_tables() -> None:
    table_names = [table.name for table in data_browser._tables()]

    assert table_names == [
        "equipment",
        "failure_modes",
        "maintenance_strategies",
        "work_order_failure_modes",
        "work_orders",
    ]
    assert data_browser._table_by_name("equipment") is not None
    assert data_browser._table_by_name("messages") is None
    assert data_browser._table_by_name("agent_runs") is None
    assert data_browser._table_by_name("missing_table") is None


def test_work_order_failure_modes_include_joined_display_columns() -> None:
    table = data_browser._table_by_name("work_order_failure_modes")

    assert table is not None
    assert data_browser._display_columns_for_table(table) == [
        "work_order_number",
        "short_text",
        "failure_mode",
        "work_order_id",
        "failure_mode_id",
        "source",
        "confidence",
        "evidence",
        "created_at",
        "id",
    ]


def test_display_columns_move_primary_id_to_last_column() -> None:
    table = Table(
        "sample_table",
        MetaData(),
        Column("id", Text),
        Column("name", Text),
        Column("description", Text),
    )

    assert data_browser._display_columns_for_table(table) == [
        "name",
        "description",
        "id",
    ]


def test_column_filters_ignore_unknown_and_empty_filters() -> None:
    table = Table(
        "sample_table",
        MetaData(),
        Column("description", Text),
    )

    filters = data_browser._column_filters(
        table,
        [
            "description=pump",
            "unknown=value",
            "description=",
            "malformed",
        ],
    )

    assert len(filters) == 1


def test_serialize_value_formats_supported_scalar_types() -> None:
    assert data_browser._serialize_value(date(2026, 1, 2)) == "2026-01-02"
    assert data_browser._serialize_value(Decimal("4.20")) == "4.20"
    assert data_browser._serialize_value(None) is None
