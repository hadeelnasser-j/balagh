"""Thread-safe in-memory repository. Used by tests and DATA_BACKEND=memory."""
from __future__ import annotations

import copy
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from app.repositories.base import NotFoundError, Row


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _matches(row: Row, filters: Row | None) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        value = row.get(key)
        if isinstance(expected, (list, tuple, set, frozenset)):
            if value not in expected:
                return False
        elif value != expected:
            return False
    return True


class MemoryRepository:
    def __init__(self) -> None:
        self._tables: dict[str, dict[str, Row]] = {}
        self._lock = threading.RLock()

    def _table(self, name: str) -> dict[str, Row]:
        return self._tables.setdefault(name, {})

    def insert(self, table: str, row: Row) -> Row:
        with self._lock:
            stored = copy.deepcopy(row)
            stored.setdefault("id", str(uuid.uuid4()))
            stored.setdefault("created_at", _now())
            stored["updated_at"] = _now()
            self._table(table)[stored["id"]] = stored
            return copy.deepcopy(stored)

    def insert_many(self, table: str, rows: list[Row]) -> list[Row]:
        return [self.insert(table, row) for row in rows]

    def get(self, table: str, row_id: str) -> Row | None:
        with self._lock:
            row = self._table(table).get(str(row_id))
            return copy.deepcopy(row) if row else None

    def update(self, table: str, row_id: str, patch: Row) -> Row:
        with self._lock:
            row = self._table(table).get(str(row_id))
            if row is None:
                raise NotFoundError(f"{table}:{row_id}")
            row.update(copy.deepcopy(patch))
            row["updated_at"] = _now()
            return copy.deepcopy(row)

    def update_where(self, table: str, filters: Row, patch: Row) -> int:
        with self._lock:
            hits = [r for r in self._table(table).values() if _matches(r, filters)]
            for row in hits:
                row.update(copy.deepcopy(patch))
                row["updated_at"] = _now()
            return len(hits)

    def list(self, table: str, filters: Row | None = None, order_by: str | None = None,
             desc: bool = False, limit: int | None = None, offset: int = 0) -> list[Row]:
        with self._lock:
            rows = [r for r in self._table(table).values() if _matches(r, filters)]
            if order_by:
                rows.sort(key=lambda r: (r.get(order_by) is None, r.get(order_by)), reverse=desc)
            rows = rows[offset:]
            if limit is not None:
                rows = rows[:limit]
            return copy.deepcopy(rows)

    def count(self, table: str, filters: Row | None = None) -> int:
        with self._lock:
            return sum(1 for r in self._table(table).values() if _matches(r, filters))

    def delete_where(self, table: str, filters: Row) -> int:
        with self._lock:
            ids = [k for k, r in self._table(table).items() if _matches(r, filters)]
            for key in ids:
                del self._table(table)[key]
            return len(ids)

    def ping(self) -> bool:
        return True

    def dump(self) -> dict[str, Any]:  # debugging helper
        with self._lock:
            return copy.deepcopy(self._tables)
