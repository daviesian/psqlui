"""Connection/session manager wiring metadata into the UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping

from .config import AppConfig, ConnectionProfileConfig
from .connections import (
    AsyncpgConnectionBackend,
    ConnectionBackend,
    ConnectionBackendError,
    ConnectionEvent,
    DemoConnectionBackend,
    MetadataListener,
    MetadataSnapshot,
)
from .sqlintel import SqlIntelService

SessionListener = Callable[["SessionState"], None]


@dataclass(frozen=True, slots=True)
class ConnectionProfile:
    """Runtime representation of a connection profile."""

    name: str
    dsn: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    user: str | None = None
    metadata_key: str | None = None
    metadata: MetadataSnapshot | None = None


@dataclass(frozen=True, slots=True)
class SessionState:
    """Current session snapshot (active connection + metadata)."""

    profile: ConnectionProfile
    connected: bool
    metadata: Mapping[str, tuple[str, ...]]
    schemas: tuple[str, ...]
    refreshed_at: datetime
    status: str = "Connected"
    latency_ms: int | None = None


class SessionManager:
    """Lightweight session orchestrator for the Textual app."""

    def __init__(
        self,
        sql_intel: SqlIntelService,
        *,
        config: AppConfig,
        backend: ConnectionBackend | None = None,
        fallback_backend: ConnectionBackend | None = None,
    ) -> None:
        self._sql_intel = sql_intel
        self._config = config
        self._profiles = tuple(self._from_config(entry) for entry in config.profiles)
        self._listeners: set[SessionListener] = set()
        self._state: SessionState | None = None
        self._backend = backend or AsyncpgConnectionBackend()
        self._fallback_backend = fallback_backend or DemoConnectionBackend()
        self._active_backends: dict[str, ConnectionBackend] = {}
        self._backend_listener = self._wrap_backend_listener(self._backend)
        self._backend_unsubscribe = self._backend.subscribe(self._backend_listener)
        self._fallback_listener = self._wrap_backend_listener(self._fallback_backend)
        self._fallback_unsubscribe = self._fallback_backend.subscribe(self._fallback_listener)
        active_name = config.active_profile or (self._profiles[0].name if self._profiles else None)
        if active_name and self._profiles:
            try:
                self.connect(active_name)
            except ConnectionBackendError:
                self._state = None

    @property
    def profiles(self) -> tuple[ConnectionProfile, ...]:
        """Profiles available in the current config."""

        return self._profiles

    @property
    def state(self) -> SessionState | None:
        """Current session state."""

        return self._state

    @property
    def active_profile_name(self) -> str | None:
        """Name of the currently active profile, if any."""

        if self._state:
            return self._state.profile.name
        return None

    @property
    def metadata_snapshot(self) -> Mapping[str, tuple[str, ...]]:
        """Latest metadata snapshot powering the query pad + sidebar."""

        if self._state:
            return self._state.metadata
        return {}

    def connect(self, name: str) -> SessionState:
        """Activate the requested profile."""

        profile = self._profile_by_name(name)
        event: ConnectionEvent
        backend = self._backend
        try:
            event = backend.connect(profile)
        except ConnectionBackendError:
            backend = self._fallback_backend
            if backend is None:
                raise
            event = backend.connect(profile)
        self._active_backends[profile.name] = backend
        self._update_state(
            profile,
            event.metadata,
            schemas=event.schemas,
            refreshed_at=event.connected_at,
            status=event.status,
            latency_ms=event.latency_ms,
        )
        return self._state

    def refresh_active_profile(self) -> None:
        """Request a metadata refresh for the active profile."""

        if not self._state:
            return
        backend = self._active_backends.get(self._state.profile.name, self._backend)
        try:
            backend.refresh(self._state.profile)
        except ConnectionBackendError:
            self._fallback_to_demo(self._state.profile)

    def refresh_profile(self, name: str) -> None:
        """Refresh metadata for the requested profile, switching if needed."""

        if self._state and self._state.profile.name == name:
            self.refresh_active_profile()
            return
        self.connect(name)
        self.refresh_active_profile()

    def subscribe(self, listener: SessionListener) -> Callable[[], None]:
        """Subscribe to session updates; returns an unsubscribe handle."""

        self._listeners.add(listener)
        if self._state:
            listener(self._state)

        def _unsubscribe() -> None:
            self._listeners.discard(listener)

        return _unsubscribe

    def _profile_by_name(self, name: str) -> ConnectionProfile:
        for profile in self._profiles:
            if profile.name == name:
                return profile
        raise ValueError(f"Profile '{name}' not found.")

    def _fallback_to_demo(self, profile: ConnectionProfile) -> None:
        event = self._fallback_backend.connect(profile)
        self._active_backends[profile.name] = self._fallback_backend
        self._update_state(
            profile,
            event.metadata,
            schemas=event.schemas,
            refreshed_at=event.connected_at,
            status=event.status,
            latency_ms=event.latency_ms,
        )

    def _from_config(self, profile: ConnectionProfileConfig) -> ConnectionProfile:
        metadata = (
            {
                table: tuple(columns)
                for table, columns in (profile.metadata or {}).items()
            }
            if profile.metadata
            else None
        )
        return ConnectionProfile(
            name=profile.name,
            dsn=profile.dsn,
            host=profile.host,
            port=profile.port,
            database=profile.database,
            user=profile.user,
            metadata_key=profile.metadata_key,
            metadata=metadata,
        )

    def _update_state(
        self,
        profile: ConnectionProfile,
        metadata: MetadataSnapshot,
        *,
        schemas: tuple[str, ...] | None = None,
        refreshed_at: datetime | None = None,
        status: str = "Connected",
        latency_ms: int | None = None,
    ) -> None:
        self._sql_intel.update_metadata(metadata)
        self._state = SessionState(
            profile=profile,
            connected=True,
            metadata=metadata,
            schemas=schemas or self._infer_schemas(metadata),
            refreshed_at=refreshed_at or datetime.now(tz=timezone.utc),
            status=status,
            latency_ms=latency_ms,
        )
        self._notify()

    def _handle_backend_event(
        self,
        profile: ConnectionProfile,
        event: ConnectionEvent,
        source: ConnectionBackend,
    ) -> None:
        if not self._state:
            return
        if profile.name != self._state.profile.name:
            return
        active = self._active_backends.get(profile.name, self._backend)
        if source is not active:
            return
        self._update_state(
            profile,
            event.metadata,
            schemas=event.schemas,
            refreshed_at=event.connected_at,
            status=event.status,
            latency_ms=event.latency_ms,
        )

    def _wrap_backend_listener(self, backend: ConnectionBackend) -> MetadataListener:
        def _callback(profile: ConnectionProfile, event: ConnectionEvent) -> None:
            self._handle_backend_event(profile, event, backend)

        return _callback

    @staticmethod
    def _infer_schemas(metadata: Mapping[str, tuple[str, ...]]) -> tuple[str, ...]:
        schemas: set[str] = set()
        for table in metadata:
            if "." in table:
                schema = table.split(".", 1)[0]
            else:
                schema = "public"
            schemas.add(schema)
        return tuple(sorted(schemas)) or ("public",)

    def _notify(self) -> None:
        if not self._state:
            return
        for listener in tuple(self._listeners):
            listener(self._state)


__all__ = [
    "ConnectionProfile",
    "SessionManager",
    "SessionState",
]
