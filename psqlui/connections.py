"""Simulated connection backend that emits metadata + health events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import random
from typing import Callable, Mapping, Sequence, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from .session import ConnectionProfile

MetadataSnapshot = Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class ConnectionEvent:
    """Snapshot emitted whenever metadata refreshes."""

    metadata: MetadataSnapshot
    status: str
    latency_ms: int
    connected_at: datetime


MetadataListener = Callable[["ConnectionProfile", ConnectionEvent], None]


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
        return ConnectionEvent(
            metadata=metadata,
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


__all__ = ["ConnectionEvent", "DemoConnectionBackend", "DEMO_METADATA_PRESETS", "MetadataSnapshot"]
