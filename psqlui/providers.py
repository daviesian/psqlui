"""Command palette providers for core app features."""

from __future__ import annotations

from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.types import IgnoreReturnCallbackType

from .session import SessionManager


class ProfileSwitchProvider(Provider):
    """Expose connection profiles to the command palette."""

    async def search(self, query: str) -> Hits:
        manager = self._session_manager
        if manager is None:
            return
        matcher = self.matcher(query)
        for profile in manager.profiles:
            match = matcher.match(profile.name)
            if match > 0:
                yield Hit(
                    score=match,
                    match_display=f"Switch to profile: {matcher.highlight(profile.name)}",
                    command=self._build_callback(profile.name),
                    help="Set the active connection profile.",
                )

    async def discover(self) -> Hits:
        manager = self._session_manager
        if manager is None:
            return
        for profile in manager.profiles:
            yield DiscoveryHit(
                display=f"Switch to profile: {profile.name}",
                command=self._build_callback(profile.name),
                help="Set the active connection profile.",
            )

    @property
    def _session_manager(self) -> SessionManager | None:
        manager = getattr(self.app, "session_manager", None)
        if isinstance(manager, SessionManager):
            return manager
        return None

    def _build_callback(self, name: str) -> IgnoreReturnCallbackType:
        async def _run() -> None:
            switcher = getattr(self.app, "switch_profile", None)
            if switcher is None:
                return
            switcher(name)

        return _run


class SessionRefreshProvider(Provider):
    """Expose a refresh action for the active session."""

    _LABEL = "Refresh active profile metadata"

    async def search(self, query: str) -> Hits:
        manager = self._session_manager
        if manager is None:
            return
        matcher = self.matcher(query)
        score = matcher.match(self._LABEL)
        if score > 0:
            yield Hit(
                score=score,
                match_display=matcher.highlight(self._LABEL),
                command=self._build_callback(),
                help="Trigger Ctrl+R equivalent refresh.",
            )

    async def discover(self) -> Hits:
        manager = self._session_manager
        if manager is None:
            return
        yield DiscoveryHit(
            display=self._LABEL,
            command=self._build_callback(),
            help="Trigger Ctrl+R equivalent refresh.",
        )

    @property
    def _session_manager(self) -> SessionManager | None:
        manager = getattr(self.app, "session_manager", None)
        if isinstance(manager, SessionManager):
            return manager
        return None

    def _build_callback(self) -> IgnoreReturnCallbackType:
        async def _run() -> None:
            manager = self._session_manager
            if manager is None:
                return
            manager.refresh_active_profile()

        return _run


__all__ = ["ProfileSwitchProvider", "SessionRefreshProvider"]
