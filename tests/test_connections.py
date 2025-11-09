"""Tests for the connection backends."""

from __future__ import annotations

from typing import Any

import pytest

from psqlui.connections import AsyncpgConnectionBackend, ConnectionBackendError, DemoConnectionBackend
from psqlui.session import ConnectionProfile


def test_backend_cycles_metadata_snapshots() -> None:
    backend = DemoConnectionBackend(
        {
            "demo": (
                {"public.accounts": ("id",)},
                {"public.accounts": ("id", "email")},
            )
        }
    )
    profile = ConnectionProfile(name="Local", metadata_key="demo")
    snapshots: list[tuple[str, ...]] = []

    event = backend.connect(profile)
    assert event.metadata["public.accounts"] == ("id",)
    assert event.schemas == ("public",)

    backend.subscribe(lambda _, ev: snapshots.append(ev.metadata["public.accounts"]))
    backend.refresh(profile)

    assert snapshots[0] == ("id", "email")


class _FakeConnection:
    def __init__(self, snapshots: list[list[dict[str, str]]]) -> None:
        self._snapshots = snapshots
        self._call = 0

    async def fetch(self, query: str) -> list[dict[str, str]]:
        assert "information_schema" in query
        if "schemata" in query:
            # Surface at least the public schema so empty DBs still show it.
            return [{"schema_name": "public"}]
        index = min(self._call, len(self._snapshots) - 1)
        self._call += 1
        return self._snapshots[index]

    async def close(self) -> None:  # pragma: no cover - nothing to clean
        return None


def test_asyncpg_backend_emits_real_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshots = [
        [
            {"table_schema": "public", "table_name": "accounts", "column_name": "id"},
            {"table_schema": "public", "table_name": "accounts", "column_name": "email"},
        ],
        [
            {"table_schema": "public", "table_name": "accounts", "column_name": "id"},
            {"table_schema": "public", "table_name": "accounts", "column_name": "email"},
            {"table_schema": "public", "table_name": "accounts", "column_name": "status"},
        ],
    ]
    fake_conn = _FakeConnection(snapshots)

    async def _fake_connect(**kwargs: Any) -> _FakeConnection:
        return fake_conn

    monkeypatch.setattr("psqlui.connections.asyncpg.connect", _fake_connect)
    backend = AsyncpgConnectionBackend()
    profile = ConnectionProfile(name="Local", host="localhost", database="postgres", user="postgres")
    events: list[tuple[str, ...]] = []
    backend.subscribe(lambda _profile, event: events.append(event.metadata["public.accounts"]))

    event = backend.connect(profile)

    try:
        assert event.metadata["public.accounts"] == ("id", "email")
        assert event.schemas and "public" in event.schemas
        backend.refresh(profile)
        assert events[-1] == ("id", "email", "status")
    finally:
        backend.shutdown()


def test_asyncpg_backend_surfaces_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _broken_connect(**kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("psqlui.connections.asyncpg.connect", _broken_connect)
    backend = AsyncpgConnectionBackend()
    profile = ConnectionProfile(name="Broken")

    try:
        with pytest.raises(ConnectionBackendError):
            backend.connect(profile)
    finally:
        backend.shutdown()
