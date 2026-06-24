from typing import Any

from pydantic import BaseModel


class DataTableSummaryResponse(BaseModel):
    name: str
    columns: list[str]
    row_count: int


class DataTablePageResponse(BaseModel):
    name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    limit: int
    offset: int
    has_more: bool
