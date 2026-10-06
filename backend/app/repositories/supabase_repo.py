"""Supabase (PostgREST) implementation of DataRepository.

Uses the service-role key server-side only. Never expose it to the frontend.
"""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from app.repositories.base import NotFoundError, Row

logger = logging.getLogger(__name__)

# Columns that exist in memory/domain objects but not in Postgres are dropped
# before writes to keep PostgREST from rejecting the payload.
_TRANSIENT_KEYS = {"latest_job"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def url_problem(url: str) -> str | None:
    """Explain an obviously wrong SUPABASE_URL (None if it looks right)."""
    if not url:
        return "SUPABASE_URL is empty"
    if "supabase.com/dashboard" in url:
        return "SUPABASE_URL is the dashboard link; use the API URL https://<project-ref>.supabase.co"
    if url.startswith("postgres") or ":5432" in url or ":6543" in url or "pooler.supabase.com" in url:
        return "SUPABASE_URL is a Postgres connection string; use the API URL https://<project-ref>.supabase.co"
    if not url.startswith("https://"):
        return "SUPABASE_URL must start with https://"
    return None


def _client_options(timeout: float) -> Any:
    """Short network timeouts so an unreachable Supabase fails fast instead of hanging requests."""
    try:
        try:
            from supabase import SyncClientOptions as Options  # supabase-py >= 2.10
        except ImportError:
            from supabase import ClientOptions as Options  # older 2.x
        return Options(postgrest_client_timeout=timeout, storage_client_timeout=max(timeout, 30))
    except Exception as exc:  # noqa: BLE001 - fall back to library defaults
        logger.warning("Could not set Supabase client timeouts: %s", exc)
        return None


class SupabaseRepository:
    def __init__(self, url: str, service_key: str, timeout: float = 10.0) -> None:
        if not url or not service_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        problem = url_problem(url)
        if problem:
            raise RuntimeError(problem)
        from supabase import create_client  # imported lazily

        options = _client_options(timeout)
        self.url = url
        self._client = create_client(url, service_key, options=options) if options else create_client(url, service_key)
        self._lock = threading.Lock()  # supabase-py's sync client is not guaranteed thread-safe

    @property
    def client(self) -> Any:
        return self._client

    def _apply_filters(self, query: Any, filters: Row | None) -> Any:
        for key, value in (filters or {}).items():
            if isinstance(value, (list, tuple, set, frozenset)):
                query = query.in_(key, list(value))
            elif value is None:
                query = query.is_(key, "null")
            else:
                query = query.eq(key, value)
        return query

    @staticmethod
    def _clean(row: Row) -> Row:
        return {k: v for k, v in row.items() if k not in _TRANSIENT_KEYS}

    def insert(self, table: str, row: Row) -> Row:
        with self._lock:
            result = self._client.table(table).insert(self._clean(row)).execute()
        return result.data[0]

    def insert_many(self, table: str, rows: list[Row]) -> list[Row]:
        if not rows:
            return []
        with self._lock:
            result = self._client.table(table).insert([self._clean(r) for r in rows]).execute()
        return list(result.data)

    def get(self, table: str, row_id: str) -> Row | None:
        try:
            uuid.UUID(str(row_id))
        except ValueError:
            return None  # not a uuid: cannot exist (avoids a Postgres cast error)
        with self._lock:
            result = self._client.table(table).select("*").eq("id", str(row_id)).limit(1).execute()
        return result.data[0] if result.data else None

    def update(self, table: str, row_id: str, patch: Row) -> Row:
        payload = {**self._clean(patch), "updated_at": _now()}
        with self._lock:
            result = self._client.table(table).update(payload).eq("id", str(row_id)).execute()
        if not result.data:
            raise NotFoundError(f"{table}:{row_id}")
        return result.data[0]

    def update_where(self, table: str, filters: Row, patch: Row) -> int:
        payload = {**self._clean(patch), "updated_at": _now()}
        with self._lock:
            query = self._apply_filters(self._client.table(table).update(payload), filters)
            result = query.execute()
        return len(result.data or [])

    def list(self, table: str, filters: Row | None = None, order_by: str | None = None,
             desc: bool = False, limit: int | None = None, offset: int = 0) -> list[Row]:
        rows: list[Row] = []
        page = 1000  # PostgREST default max rows
        start = offset
        while True:
            want = page if limit is None else min(page, limit - len(rows))
            if want <= 0:
                break
            with self._lock:
                query = self._apply_filters(self._client.table(table).select("*"), filters)
                if order_by:
                    query = query.order(order_by, desc=desc)
                result = query.range(start, start + want - 1).execute()
            batch = list(result.data or [])
            rows.extend(batch)
            if len(batch) < want:
                break
            start += want
        return rows

    def count(self, table: str, filters: Row | None = None) -> int:
        with self._lock:
            query = self._apply_filters(self._client.table(table).select("id", count="exact"), filters)
            result = query.limit(1).execute()
        return int(result.count or 0)

    def delete_where(self, table: str, filters: Row) -> int:
        if not filters:
            raise ValueError("Refusing to delete without filters")
        with self._lock:
            result = self._apply_filters(self._client.table(table).delete(), filters).execute()
        return len(result.data or [])

    def ping(self) -> bool:
        try:
            with self._lock:
                self._client.table("projects").select("id").limit(1).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Supabase not reachable at %s: %s: %s", self.url, type(exc).__name__, exc)
            return False
