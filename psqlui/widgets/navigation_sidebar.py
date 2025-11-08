"""Sidebar widget showing connection/session metadata."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from psqlui.session import SessionManager, SessionState


class NavigationSidebar(Container):
    """Displays the active profile and schemas pulled from the session manager."""

    DEFAULT_CSS = """
    NavigationSidebar {
        width: 28;
        min-width: 22;
        border-right: solid $surface-darken-1;
        padding: 1;
        height: 1fr;
        background: $surface-darken-2;
    }

    NavigationSidebar .sidebar-heading {
        text-style: bold;
        margin-bottom: 1;
    }

    NavigationSidebar .sidebar-section {
        margin-bottom: 2;
    }
    """

    def __init__(self, session_manager: SessionManager) -> None:
        super().__init__(id="nav-sidebar")
        self._session_manager = session_manager
        self._connections: Static | None = None
        self._schemas: Static | None = None
        self._unsubscribe: Callable[[], None] | None = None

    def compose(self) -> ComposeResult:
        yield Static("Connections", classes="sidebar-heading")
        self._connections = Static("Loading profiles...", id="connection-list", classes="sidebar-section")
        yield self._connections
        yield Static("Schemas", classes="sidebar-heading")
        self._schemas = Static("No schemas loaded.", id="schema-list", classes="sidebar-section")
        yield self._schemas

    async def on_mount(self) -> None:
        self._unsubscribe = self._session_manager.subscribe(self._handle_session_update)

    def on_unmount(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    def _handle_session_update(self, state: SessionState) -> None:
        self._render_connections(state)
        self._render_schemas(state)

    def _render_connections(self, state: SessionState) -> None:
        if not self._connections:
            return
        lines = []
        for profile in self._session_manager.profiles:
            marker = "*" if profile.name == state.profile.name else " "
            lines.append(f"{marker} {profile.name}")
        if not lines:
            lines = ["No profiles configured."]
        self._connections.update("\n".join(lines))

    def _render_schemas(self, state: SessionState) -> None:
        if not self._schemas:
            return
        metadata = state.metadata
        if not metadata:
            self._schemas.update("No schemas loaded.")
            return
        buckets: dict[str, list[str]] = defaultdict(list)
        for table in sorted(metadata):
            if "." in table:
                schema, rel = table.split(".", 1)
            else:
                schema, rel = "public", table
            buckets[schema].append(rel)
        lines: list[str] = []
        for schema in sorted(buckets):
            lines.append(schema)
            for rel in buckets[schema][:5]:
                lines.append(f"  - {rel}")
        self._schemas.update("\n".join(lines))


__all__ = ["NavigationSidebar"]
