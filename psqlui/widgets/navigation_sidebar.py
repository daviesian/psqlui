"""Sidebar widget showing connection/session metadata."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, ListItem, ListView, Static

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

    #profile-list {
        height: 6;
        border: round $primary 30%;
        margin-bottom: 2;
    }

    #profile-list .active {
        text-style: bold;
    }

    #profile-summary {
        padding-top: 1;
        border-top: solid $surface-darken-1;
        color: $text-muted;
        min-height: 4;
    }

    """

    def __init__(self, session_manager: SessionManager) -> None:
        super().__init__(id="nav-sidebar")
        self._session_manager = session_manager
        self._profile_list: ListView | None = None
        self._profile_items: dict[str, _ProfileListItem] = {}
        self._schemas: Static | None = None
        self._profile_summary: Static | None = None
        self._unsubscribe: Callable[[], None] | None = None

    def compose(self) -> ComposeResult:
        yield Static("Connections", classes="sidebar-heading")
        items = [_ProfileListItem(profile.name) for profile in self._session_manager.profiles]
        self._profile_items = {item.profile_name: item for item in items}
        self._profile_list = ListView(*items, id="profile-list")
        yield self._profile_list
        self._profile_summary = Static("", id="profile-summary", classes="sidebar-section")
        yield self._profile_summary
        yield Static("Schemas", classes="sidebar-heading")
        self._schemas = Static("No schemas loaded.", id="schema-list", classes="sidebar-section")
        yield self._schemas

    async def on_mount(self) -> None:
        self._unsubscribe = self._session_manager.subscribe(self._handle_session_update)

    def on_unmount(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    async def on_resize(self, event: events.Resize) -> None:
        self._report_width(event.size.width)

    def _handle_session_update(self, state: SessionState) -> None:
        self._render_connections(state)
        self._render_schemas(state)
        self._render_profile_summary(state)

    def _render_connections(self, state: SessionState) -> None:
        if not self._profile_list:
            return
        profiles = list(self._session_manager.profiles)
        active_index = 0
        for idx, profile in enumerate(profiles):
            item = self._profile_items.get(profile.name)
            if item is None:
                continue
            item.set_class(profile.name == state.profile.name, "active")
            if profile.name == state.profile.name:
                active_index = idx
        if profiles:
            self._profile_list.index = active_index

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

    @on(ListView.Selected)
    def _handle_profile_selected(self, event: ListView.Selected) -> None:
        if self._profile_list is None or event.list_view.id != "profile-list":
            return
        item = event.item
        if isinstance(item, _ProfileListItem):
            self._request_switch(item.profile_name)

    def _request_switch(self, name: str) -> None:
        switcher = getattr(self.app, "switch_profile", None)
        if switcher is None:
            return
        switcher(name)

    def _render_profile_summary(self, state: SessionState) -> None:
        if not self._profile_summary:
            return
        host = state.profile.host or "localhost"
        database = state.profile.database or state.profile.name
        latency = f"{state.latency_ms} ms" if state.latency_ms is not None else "—"
        schema_count = len(state.metadata)
        table_count = sum(len(columns) for columns in state.metadata.values())
        summary = "\n".join(
            [
                f"Profile: {state.profile.name}",
                f"Host: {host}",
                f"Database: {database}",
                f"Schemas: {schema_count} · Tables: {table_count}",
                f"Status: {state.status} ({latency})",
            ]
        )
        self._profile_summary.update(summary)

    def _report_width(self, width: int) -> None:
        remember = getattr(self.app, "remember_sidebar_width", None)
        if remember is None:
            return
        if width > 0:
            remember(width)


class _ProfileListItem(ListItem):
    """List item storing a profile name for selection callbacks."""

    def __init__(self, name: str) -> None:
        super().__init__(Label(name))
        self.profile_name = name


__all__ = ["NavigationSidebar"]
