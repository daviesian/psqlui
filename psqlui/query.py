"""Query execution services for the query pad and plugins."""

from __future__ import annotations
import random
import time
from dataclasses import dataclass
from typing import Iterable, Protocol

import asyncpg

from .models import ConnectionProfile


class QueryExecutionError(RuntimeError):
    """Raised when a query fails to execute."""


@dataclass(frozen=True, slots=True)
class QueryResult:
    """Normalized query output returned to the UI."""

    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    status: str
    elapsed_ms: int
    row_count: int | None = None


class QueryExecutor(Protocol):
    """Interface implemented by query executors."""

    async def execute(self, profile: ConnectionProfile, sql: str) -> QueryResult: ...


class AsyncpgQueryExecutor:
    """Runs SQL statements against PostgreSQL via asyncpg."""

    def __init__(self, *, connect_timeout: float = 5.0) -> None:
        self._connect_timeout = connect_timeout

    async def execute(self, profile: ConnectionProfile, sql: str) -> QueryResult:
        statement = sql.strip()
        if not statement:
            raise QueryExecutionError("Provide SQL to execute.")
        started = time.perf_counter()
        conn = await asyncpg.connect(**self._connect_kwargs(profile))
        try:
            if _returns_rows(statement):
                records = await conn.fetch(statement)
                result = _records_to_result(records)
                status = f"{result['row_count']} row(s)" if result["row_count"] is not None else "OK"
                columns = result["columns"]
                rows = result["rows"]
                row_count = result["row_count"]
            else:
                status = await conn.execute(statement)
                columns = ()
                rows = ()
                row_count = None
        except Exception as exc:  # pragma: no cover - exercised via tests
            raise QueryExecutionError(str(exc)) from exc
        finally:
            try:
                await conn.close()
            except Exception:  # pragma: no cover - best effort cleanup
                pass
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return QueryResult(
            columns=columns,
            rows=rows,
            status=status,
            elapsed_ms=elapsed_ms,
            row_count=row_count,
        )

    def _connect_kwargs(self, profile: ConnectionProfile) -> dict[str, object]:
        kwargs: dict[str, object] = {}
        if profile.dsn:
            kwargs["dsn"] = profile.dsn
        else:
            kwargs["host"] = profile.host or "localhost"
            if profile.port is not None:
                kwargs["port"] = profile.port
            if profile.user:
                kwargs["user"] = profile.user
            if profile.database:
                kwargs["database"] = profile.database
        kwargs.setdefault("timeout", self._connect_timeout)
        return kwargs


class DemoQueryExecutor:
    """Returns fake result sets when the demo backend is active."""

    def __init__(self, *, row_count: int = 5) -> None:
        self._row_count = row_count

    async def execute(self, profile: ConnectionProfile, sql: str) -> QueryResult:
        metadata = profile.metadata or {}
        if metadata:
            table, columns = next(iter(metadata.items()))
        else:
            table, columns = profile.metadata_key or profile.name or "demo", ("id", "value")
        columns = columns or ("demo",)
        rows = []
        for idx in range(self._row_count):
            row = tuple(f"{col}_{idx}" for col in columns)
            rows.append(row)
        elapsed = random.randint(5, 25)
        status = f"Demo result for {table}"
        return QueryResult(
            columns=tuple(columns),
            rows=tuple(rows),
            status=status,
            elapsed_ms=elapsed,
            row_count=len(rows),
        )


def _returns_rows(statement: str) -> bool:
    token = statement.lstrip().split(None, 1)
    if not token:
        return False
    head = token[0].lower()
    return head in {"select", "with", "show", "values"}


def _records_to_result(records: Iterable[asyncpg.Record]) -> dict[str, object]:
    rows: list[tuple[object, ...]] = []
    columns: tuple[str, ...] = ()
    for record in records:
        if not columns:
            keys = tuple(record.keys()) if hasattr(record, "keys") else tuple(range(len(record)))
            columns = tuple(str(key) for key in keys)
        if not columns:
            continue
        rows.append(tuple(record[key] for key in columns))
    return {"columns": columns, "rows": tuple(rows), "row_count": len(rows)}


__all__ = [
    "AsyncpgQueryExecutor",
    "DemoQueryExecutor",
    "QueryExecutionError",
    "QueryExecutor",
    "QueryResult",
]
