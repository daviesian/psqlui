"""Status bar widget that mirrors session information."""

from __future__ import annotations

from typing import Callable

from textual.widgets import Static

from psqlui.session import SessionManager, SessionState


class StatusBar(Static):
    """Compact status strip rendered above Textual's footer."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        padding: 0 1;
        background: $surface-darken-3;
        color: $text;
    }
    """

    def __init__(self, session_manager: SessionManager) -> None:
        super().__init__("", id="status-bar")
        self._session_manager = session_manager
        self._unsubscribe: Callable[[], None] | None = None

    async def on_mount(self) -> None:
        self._unsubscribe = self._session_manager.subscribe(self._handle_session_update)

    def on_unmount(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    def _handle_session_update(self, state: SessionState) -> None:
        tables = len(state.metadata)
        schemas = len({table.split(".")[0] if "." in table else "public" for table in state.metadata})
        status = state.status or ("Connected" if state.connected else "Idle")
        latency = f"{state.latency_ms} ms" if state.latency_ms is not None else "—"
        refreshed = state.refreshed_at.astimezone().strftime("%H:%M:%S")
        backend = state.backend_label or ("Demo fallback" if state.using_fallback else "Primary backend")
        parts = [
            f"Profile: {state.profile.name}",
            f"Backend: {backend}",
            f"Schemas: {schemas}",
            f"Tables: {tables}",
            f"Status: {status} ({latency})",
            f"Refreshed: {refreshed}",
        ]
        if state.last_error:
            reason = state.last_error.splitlines()[0][:80]
            parts.append(f"Error: {reason}")
        self.update(" | ".join(parts))


__all__ = ["StatusBar"]
