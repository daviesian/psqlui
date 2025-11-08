"""Connection/session manager wiring demo metadata into the UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from .config import AppConfig, ConnectionProfileConfig
from .sqlintel import SqlIntelService

MetadataSnapshot = Mapping[str, Sequence[str]]
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


DEFAULT_METADATA_PRESETS: dict[str, Mapping[str, tuple[str, ...]]] = {
    "demo": {
        "public.accounts": ("id", "email", "last_login"),
        "public.orders": ("id", "account_id", "total"),
        "public.payments": ("id", "order_id", "amount"),
    },
    "analytics": {
        "analytics.sessions": ("id", "user_id", "started_at", "device"),
        "analytics.events": ("id", "session_id", "name", "payload"),
    },
}


class SessionManager:
    """Lightweight session orchestrator for the Textual demo."""

    def __init__(
        self,
        sql_intel: SqlIntelService,
        *,
        config: AppConfig,
        metadata_presets: Mapping[str, Mapping[str, Sequence[str]]] | None = None,
    ) -> None:
        self._sql_intel = sql_intel
        self._config = config
        self._metadata_presets = {
            key: {
                table: tuple(columns)
                for table, columns in preset.items()
            }
            for key, preset in (metadata_presets or DEFAULT_METADATA_PRESETS).items()
        }
        self._profiles = tuple(self._from_config(entry) for entry in config.profiles)
        self._listeners: set[SessionListener] = set()
        self._state: SessionState | None = None
        active_name = config.active_profile or (self._profiles[0].name if self._profiles else None)
        if active_name and self._profiles:
            self.connect(active_name)

    @property
    def profiles(self) -> tuple[ConnectionProfile, ...]:
        """Profiles available in the current config."""

        return self._profiles

    @property
    def state(self) -> SessionState | None:
        """Current session state."""

        return self._state

    @property
    def metadata_snapshot(self) -> Mapping[str, tuple[str, ...]]:
        """Latest metadata snapshot powering the query pad + sidebar."""

        if self._state:
            return self._state.metadata
        return {}

    def connect(self, name: str) -> SessionState:
        """Activate the requested profile."""

        profile = self._profile_by_name(name)
        metadata = self._resolve_metadata(profile)
        self._sql_intel.update_metadata(metadata)
        self._state = SessionState(profile=profile, connected=True, metadata=metadata)
        self._notify()
        return self._state

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

    def _resolve_metadata(self, profile: ConnectionProfile) -> Mapping[str, tuple[str, ...]]:
        if profile.metadata:
            return profile.metadata
        if profile.metadata_key and profile.metadata_key in self._metadata_presets:
            return self._metadata_presets[profile.metadata_key]
        if self._metadata_presets:
            return next(iter(self._metadata_presets.values()))
        return {}

    def _notify(self) -> None:
        if not self._state:
            return
        for listener in tuple(self._listeners):
            listener(self._state)


__all__ = [
    "ConnectionProfile",
    "DEFAULT_METADATA_PRESETS",
    "SessionManager",
    "SessionState",
]
