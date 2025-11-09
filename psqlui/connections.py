"""Connection backends powering the session manager."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import random
import threading
import time
from typing import Any, Callable, Coroutine, Mapping, Protocol, Sequence, runtime_checkable

import asyncpg

from .models import ConnectionProfile, MetadataSnapshot


class ConnectionBackendError(RuntimeError):
    """Raised when a backend cannot connect or refresh metadata."""


@runtime_checkable
class ConnectionBackend(Protocol):
    """Protocol implemented by connection backends."""

    def connect(self, profile: "ConnectionProfile") -> "ConnectionEvent":
        """Connect to the profile and return its initial metadata."""

    def refresh(self, profile: "ConnectionProfile") -> None:
        """Refresh metadata for the profile (may emit asynchronously)."""

    def subscribe(self, listener: "MetadataListener") -> Callable[[], None]:
        """Subscribe to metadata events; returns an unsubscribe handle."""


@dataclass(frozen=True, slots=True)
class ConnectionEvent:
    """Snapshot emitted whenever metadata refreshes."""

    metadata: MetadataSnapshot
    schemas: tuple[str, ...]
    status: str
    latency_ms: int
    connected_at: datetime


MetadataListener = Callable[["ConnectionProfile", ConnectionEvent], None]


class AsyncpgConnectionBackend:
    """Connection backend that queries PostgreSQL via asyncpg."""

    _METADATA_QUERY = """
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name, ordinal_position
    """

    _SCHEMA_QUERY = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
        ORDER BY schema_name
    """

    def __init__(self, metadata_query: str | None = None, *, connect_timeout: float = 3.0) -> None:
        self._metadata_query = metadata_query or self._METADATA_QUERY
        self._schema_query = self._SCHEMA_QUERY
        self._connect_timeout = connect_timeout
        self._listeners: set[MetadataListener] = set()
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever,
            name="psqlui-asyncpg-backend",
            daemon=True,
        )
        self._loop_thread.start()

    def connect(self, profile: "ConnectionProfile") -> ConnectionEvent:
        event = self._run(self._connect(profile))
        self._emit(profile, event)
        return event

    def refresh(self, profile: "ConnectionProfile") -> None:
        event = self._run(self._refresh(profile))
        self._emit(profile, event)

    def subscribe(self, listener: MetadataListener) -> Callable[[], None]:
        self._listeners.add(listener)

        def _unsubscribe() -> None:
            self._listeners.discard(listener)

        return _unsubscribe

    def shutdown(self) -> None:
        """Stop the background event loop (testing helper)."""

        if not self._loop.is_running():  # pragma: no cover - defensive
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop_thread.join(timeout=1)

    def __del__(self) -> None:  # pragma: no cover - best effort cleanup
        try:
            self.shutdown()
        except Exception:
            pass

    def _emit(self, profile: "ConnectionProfile", event: ConnectionEvent) -> None:
        for listener in tuple(self._listeners):
            listener(profile, event)

    def _run(self, coro: Coroutine[Any, Any, ConnectionEvent]) -> ConnectionEvent:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    async def _connect(self, profile: "ConnectionProfile") -> ConnectionEvent:
        metadata, schemas, latency_ms = await self._fetch_metadata(profile)
        return ConnectionEvent(
            metadata=metadata,
            schemas=schemas,
            status="Connected",
            latency_ms=latency_ms,
            connected_at=datetime.now(tz=timezone.utc),
        )

    async def _refresh(self, profile: "ConnectionProfile") -> ConnectionEvent:
        metadata, schemas, latency_ms = await self._fetch_metadata(profile)
        return ConnectionEvent(
            metadata=metadata,
            schemas=schemas,
            status="Healthy",
            latency_ms=latency_ms,
            connected_at=datetime.now(tz=timezone.utc),
        )

    async def _fetch_metadata(self, profile: "ConnectionProfile") -> tuple[MetadataSnapshot, tuple[str, ...], int]:
        started = time.perf_counter()
        conn = await self._connect_profile(profile)
        try:
            rows = await conn.fetch(self._metadata_query)
            schema_rows = await conn.fetch(self._schema_query)
        except Exception as exc:
            raise ConnectionBackendError(f"Failed to fetch metadata for '{profile.name}': {exc}") from exc
        finally:
            try:
                await conn.close()
            except Exception:  # pragma: no cover - best effort
                pass
        latency_ms = int((time.perf_counter() - started) * 1000)
        metadata: dict[str, list[str]] = {}
        schemas: set[str] = set()
        for row in rows:
            schema = str(row["table_schema"])
            table = str(row["table_name"])
            column = str(row["column_name"])
            key = f"{schema}.{table}"
            metadata.setdefault(key, []).append(column)
            schemas.add(schema)
        for row in schema_rows:
            schemas.add(str(row["schema_name"]))
        schema_list = tuple(sorted(schemas)) or ("public",)
        return {table: tuple(columns) for table, columns in metadata.items()}, schema_list, latency_ms

    async def _connect_profile(self, profile: "ConnectionProfile"):
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
        try:
            return await asyncpg.connect(**kwargs)
        except Exception as exc:  # pragma: no cover - exercised via tests
            raise ConnectionBackendError(f"Failed to connect to profile '{profile.name}': {exc}") from exc


DEMO_METADATA_PRESETS: Mapping[str, Sequence[Mapping[str, Sequence[str]]]] = {
    "demo": (
        {
            "public.accounts": ("id", "email", "last_login"),
            "public.orders": ("id", "account_id", "total"),
            "public.payments": ("id", "order_id", "amount"),
        },
        {
            "public.accounts": ("id", "email", "last_login", "status"),
            "public.orders": ("id", "account_id", "total", "currency"),
            "public.payments": ("id", "order_id", "amount"),
        },
    ),
    "analytics": (
        {
            "analytics.sessions": ("id", "user_id", "started_at", "device"),
            "analytics.events": ("id", "session_id", "name", "payload"),
        },
        {
            "analytics.sessions": ("id", "user_id", "started_at", "device", "country"),
            "analytics.events": ("id", "session_id", "name", "payload", "metadata"),
        },
    ),
}


class DemoConnectionBackend:
    """Stub connection backend that cycles through preset metadata snapshots."""

    def __init__(
        self,
        metadata_sequences: Mapping[str, Sequence[Mapping[str, Sequence[str]]]] | None = None,
    ) -> None:
        sources = metadata_sequences or DEMO_METADATA_PRESETS
        self._presets: dict[str, tuple[MetadataSnapshot, ...]] = {
            key: tuple(self._normalize(snapshot) for snapshot in snapshots)
            for key, snapshots in sources.items()
        }
        self._cursors: dict[str, int] = {key: 0 for key in self._presets}
        self._listeners: set[MetadataListener] = set()

    def connect(self, profile: "ConnectionProfile") -> ConnectionEvent:
        """Simulate connecting to a profile and emit its metadata."""

        metadata = self._metadata_for(profile, advance=False)
        event = self._build_event(profile, metadata, status="Connected")
        self._emit(profile, event)
        return event

    def refresh(self, profile: "ConnectionProfile") -> None:
        """Emit the next metadata snapshot for the given profile."""

        metadata = self._metadata_for(profile, advance=True)
        status = random.choice(["Healthy", "Syncing", "Degraded"])
        event = self._build_event(profile, metadata, status=status)
        self._emit(profile, event)

    def emit_metadata(self, profile: "ConnectionProfile", metadata: Mapping[str, Sequence[str]]) -> None:
        """Push a custom metadata snapshot to listeners (testing helper)."""

        event = self._build_event(profile, self._normalize(metadata), status="Updated")
        self._emit(profile, event)

    def subscribe(self, listener: MetadataListener) -> Callable[[], None]:
        """Subscribe to metadata events."""

        self._listeners.add(listener)

        def _unsubscribe() -> None:
            self._listeners.discard(listener)

        return _unsubscribe

    def _metadata_for(self, profile: "ConnectionProfile", *, advance: bool) -> MetadataSnapshot:
        if profile.metadata:
            return {
                table: tuple(columns)
                for table, columns in profile.metadata.items()
            }
        key = profile.metadata_key or profile.name
        snapshots = self._presets.get(key)
        if not snapshots:
            return {}
        if advance and len(snapshots) > 1:
            self._cursors[key] = (self._cursors[key] + 1) % len(snapshots)
        idx = self._cursors.get(key, 0)
        return snapshots[idx]

    def _emit(self, profile: "ConnectionProfile", event: ConnectionEvent) -> None:
        for listener in tuple(self._listeners):
            listener(profile, event)

    def _build_event(
        self,
        profile: "ConnectionProfile",
        metadata: MetadataSnapshot,
        *,
        status: str,
    ) -> ConnectionEvent:
        latency = self._latency_for(profile)
        schemas = self._schemas_for(profile, metadata)
        return ConnectionEvent(
            metadata=metadata,
            schemas=schemas,
            status=status,
            latency_ms=latency,
            connected_at=datetime.now(tz=timezone.utc),
        )

    @staticmethod
    def _normalize(snapshot: Mapping[str, Sequence[str]]) -> MetadataSnapshot:
        return {
            table: tuple(columns)
            for table, columns in snapshot.items()
        }

    def _latency_for(self, profile: "ConnectionProfile") -> int:
        key = profile.metadata_key or profile.name
        base = 25 if key == "demo" else 55
        jitter = random.randint(0, 15)
        return base + jitter

    def _schemas_for(self, profile: "ConnectionProfile", metadata: MetadataSnapshot) -> tuple[str, ...]:
        schemas: set[str] = set()
        for table in metadata:
            if "." in table:
                schema, _ = table.split(".", 1)
            else:
                schema = "public"
            schemas.add(schema)
        if not schemas:
            schemas.add(profile.metadata_key or profile.name or "public")
        return tuple(sorted(schemas))


__all__ = [
    "AsyncpgConnectionBackend",
    "ConnectionBackend",
    "ConnectionBackendError",
    "ConnectionEvent",
    "DemoConnectionBackend",
    "DEMO_METADATA_PRESETS",
    "MetadataSnapshot",
]
