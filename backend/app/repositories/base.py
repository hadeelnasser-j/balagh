"""Storage-agnostic data repository interface for project and processing data."""
from __future__ import annotations

from typing import Any, Protocol

Row = dict[str, Any]


class DataRepository(Protocol):
    """Minimal table API implemented by the Supabase and in-memory backends.

    Filters are equality filters. Values given as a list/tuple/set mean "IN".
    """

    def insert(self, table: str, row: Row) -> Row: ...

    def insert_many(self, table: str, rows: list[Row]) -> list[Row]: ...

    def get(self, table: str, row_id: str) -> Row | None: ...

    def update(self, table: str, row_id: str, patch: Row) -> Row: ...

    def update_where(self, table: str, filters: Row, patch: Row) -> int: ...

    def list(self, table: str, filters: Row | None = None, order_by: str | None = None,
             desc: bool = False, limit: int | None = None, offset: int = 0) -> list[Row]: ...

    def count(self, table: str, filters: Row | None = None) -> int: ...

    def delete_where(self, table: str, filters: Row) -> int: ...

    def ping(self) -> bool: ...


class NotFoundError(LookupError):
    pass
