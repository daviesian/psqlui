"""Tests for query execution helpers."""

from __future__ import annotations

import pytest

from psqlui.models import ConnectionProfile
from psqlui.query import AsyncpgQueryExecutor, DemoQueryExecutor, QueryExecutionError


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _FakeConnection:
    def __init__(self, rows=None, status: str = "INSERT 0 1") -> None:
        self.rows = rows or []
        self.status = status
        self.closed = False
        self.fetch_called = False
        self.execute_called = False

    async def fetch(self, _sql: str):
        self.fetch_called = True
        return self.rows

    async def execute(self, _sql: str) -> str:
        self.execute_called = True
        return self.status

    async def close(self) -> None:
        self.closed = True


@pytest.mark.anyio
async def test_asyncpg_executor_fetches_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {"id": 1, "email": "alice@example.com"},
        {"id": 2, "email": "bob@example.com"},
    ]
    connection = _FakeConnection(rows=rows)

    async def _connect(**kwargs):  # type: ignore[no-untyped-def]
        return connection

    monkeypatch.setattr("psqlui.query.asyncpg.connect", _connect)
    executor = AsyncpgQueryExecutor()
    profile = ConnectionProfile(name="Local", database="postgres", user="postgres")

    result = await executor.execute(profile, "SELECT * FROM accounts")

    assert result.columns == ("id", "email")
    assert result.row_count == 2
    assert connection.fetch_called is True
    assert connection.closed is True


@pytest.mark.anyio
async def test_asyncpg_executor_handles_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = _FakeConnection(status="INSERT 0 1")

    async def _connect(**kwargs):  # type: ignore[no-untyped-def]
        return connection

    monkeypatch.setattr("psqlui.query.asyncpg.connect", _connect)
    executor = AsyncpgQueryExecutor()
    profile = ConnectionProfile(name="Local")

    result = await executor.execute(profile, "INSERT INTO demo VALUES (1)")

    assert result.columns == ()
    assert result.rows == ()
    assert connection.execute_called is True


@pytest.mark.anyio
async def test_asyncpg_executor_rejects_empty_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _connect(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("should not connect")

    monkeypatch.setattr("psqlui.query.asyncpg.connect", _connect)
    executor = AsyncpgQueryExecutor()
    profile = ConnectionProfile(name="Local")

    with pytest.raises(QueryExecutionError):
        await executor.execute(profile, "   ")


@pytest.mark.anyio
async def test_demo_executor_uses_metadata() -> None:
    profile = ConnectionProfile(
        name="Demo",
        metadata={"public.accounts": ("id", "email")},
    )
    executor = DemoQueryExecutor(row_count=3)

    result = await executor.execute(profile, "SELECT * FROM public.accounts")

    assert result.columns == ("id", "email")
    assert len(result.rows) == 3
