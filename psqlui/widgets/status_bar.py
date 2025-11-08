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
        status = "Connected" if state.connected else "Idle"
        self.update(f"Profile: {state.profile.name} | Schemas: {schemas} | Tables: {tables} | Status: {status}")


__all__ = ["StatusBar"]
