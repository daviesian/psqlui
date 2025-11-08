"""Demo connection backend that simulates metadata refresh events."""

from __future__ import annotations

from typing import Callable, Mapping, Sequence, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from .session import ConnectionProfile

MetadataSnapshot = Mapping[str, tuple[str, ...]]
MetadataListener = Callable[["ConnectionProfile", MetadataSnapshot], None]


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

    def connect(self, profile: "ConnectionProfile") -> MetadataSnapshot:
        """Simulate connecting to a profile and emit its metadata."""

        metadata = self._metadata_for(profile, advance=False)
        return metadata

    def refresh(self, profile: "ConnectionProfile") -> None:
        """Emit the next metadata snapshot for the given profile."""

        metadata = self._metadata_for(profile, advance=True)
        self._emit(profile, metadata)

    def emit_metadata(self, profile: "ConnectionProfile", metadata: Mapping[str, Sequence[str]]) -> None:
        """Push a custom metadata snapshot to listeners (testing helper)."""

        self._emit(profile, self._normalize(metadata))

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

    def _emit(self, profile: "ConnectionProfile", metadata: MetadataSnapshot) -> None:
        for listener in tuple(self._listeners):
            listener(profile, metadata)

    @staticmethod
    def _normalize(snapshot: Mapping[str, Sequence[str]]) -> MetadataSnapshot:
        return {
            table: tuple(columns)
            for table, columns in snapshot.items()
        }


__all__ = ["DemoConnectionBackend", "DEMO_METADATA_PRESETS", "MetadataSnapshot"]
