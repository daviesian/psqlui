"""Sidebar widget showing connection/session metadata."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView, Static

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
        self._context_menu: _ProfileContextMenu | None = None
        self._unsubscribe: Callable[[], None] | None = None

    def compose(self) -> ComposeResult:
        yield Static("Connections", classes="sidebar-heading")
        items = [_ProfileListItem(profile.name) for profile in self._session_manager.profiles]
        self._profile_items = {item.profile_name: item for item in items}
        self._profile_list = _ProfileListView(*items, id="profile-list")
        yield self._profile_list
        self._context_menu = _ProfileContextMenu(self._handle_profile_action)
        yield self._context_menu
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
            self._dismiss_context_menu()
            self._request_switch(item.profile_name)
            event.stop()

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

    def _handle_profile_action(self, action: str, profile_name: str) -> None:
        if action == "switch":
            self._request_switch(profile_name)
            return
        if action == "refresh":
            self._refresh_profile(profile_name)

    def _refresh_profile(self, profile_name: str) -> None:
        try:
            self._session_manager.refresh_profile(profile_name)
        except ValueError as exc:
            self.notify(str(exc), severity="error")

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 1 and self._context_menu and self._context_menu.is_visible:
            if not self._context_menu.owns(event.control):
                self._context_menu.hide()

    def on_key(self, event: events.Key) -> None:
        if event.key == "m":
            if self._show_context_menu_for_current():
                event.stop()
        elif event.key in {"shift+f10", "f10"}:
            if self._show_context_menu_for_current():
                event.stop()

    def on_profile_context_requested(self, event: "_ProfileContextRequested") -> None:
        if not self._context_menu:
            return
        self._context_menu.show(event.profile_name)
        event.stop()

    def _dismiss_context_menu(self) -> None:
        if self._context_menu and self._context_menu.is_visible:
            self._context_menu.hide()

    def _show_context_menu_for_current(self) -> bool:
        if not self._context_menu or not self._profile_list:
            return False
        item = self._profile_list.highlighted_child
        if not isinstance(item, _ProfileListItem):
            return False
        self._context_menu.show(item.profile_name)
        return True


class _ProfileListView(ListView):
    """ListView with a binding to surface the context menu via keyboard."""

    BINDINGS = ListView.BINDINGS + [
        Binding("m", "profile_menu", "Profile menu", show=False),
        Binding("shift+f10", "profile_menu", "Profile menu", show=False),
    ]

    def action_profile_menu(self) -> None:
        item = self.highlighted_child
        if isinstance(item, _ProfileListItem):
            self.post_message(_ProfileContextRequested(item.profile_name))


class _ProfileListItem(ListItem):
    """List item storing a profile name for selection callbacks."""

    def __init__(self, name: str) -> None:
        super().__init__(Label(name))
        self.profile_name = name

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 3:
            event.stop()
            self.post_message(_ProfileContextRequested(self.profile_name))
            return


class _ProfileContextMenu(Container):
    """Lightweight inline context menu for connection items."""

    DEFAULT_CSS = """
    #profile-context-menu {
        border: round $surface-darken-1;
        padding: 1;
        margin-bottom: 1;
        background: $surface-darken-2;
    }

    #profile-context-menu .context-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #profile-context-menu Button {
        width: 1fr;
        margin-top: 1;
    }
    """

    def __init__(self, action_handler: Callable[[str, str], None]) -> None:
        super().__init__(id="profile-context-menu", classes="sidebar-section")
        self._on_action = action_handler
        self._profile_name: str | None = None
        self._title = Label("", classes="context-title")
        self._switch_button = Button("Activate profile", id="context-switch", flat=True, compact=True)
        self._refresh_button = Button("Refresh metadata", id="context-refresh", flat=True, compact=True)
        self._buttons: tuple[Button, Button] = (self._switch_button, self._refresh_button)
        self._focused_index = 0
        self.display = False

    @property
    def is_visible(self) -> bool:
        return bool(self.display)

    def compose(self) -> ComposeResult:
        yield self._title
        yield self._switch_button
        yield self._refresh_button

    def show(self, profile_name: str) -> None:
        self._profile_name = profile_name
        self._title.update(f"Actions for {profile_name}")
        self.display = True
        self._focused_index = 0
        self.call_later(self._focus_current_button)

    def hide(self) -> None:
        self.display = False
        self._profile_name = None
        self._focused_index = 0
        self._focus_profile_list()

    def owns(self, widget: Widget | None) -> bool:
        node = widget
        while node is not None:
            if node is self:
                return True
            node = getattr(node, "parent", None)
        return False

    @on(Button.Pressed)
    def _handle_button_pressed(self, event: Button.Pressed) -> None:
        if not self._profile_name:
            return
        action = None
        if event.button.id == "context-switch":
            action = "switch"
        elif event.button.id == "context-refresh":
            action = "refresh"
        if action:
            self._on_action(action, self._profile_name)
            self.hide()
            event.stop()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.hide()
            event.stop()
            return
        if event.key == "up":
            self._move_focus(-1)
            event.stop()
            return
        if event.key == "down":
            self._move_focus(1)
            event.stop()

    def _move_focus(self, delta: int) -> None:
        total = len(self._buttons)
        if total == 0:
            return
        self._focused_index = (self._focused_index + delta) % total
        self._focus_current_button()

    def _focus_current_button(self) -> None:
        try:
            button = self._buttons[self._focused_index]
        except IndexError:
            return
        button.focus()

    def _focus_profile_list(self) -> None:
        if not self.parent:
            return
        try:
            list_view = self.parent.query_one("#profile-list", ListView)
        except Exception:  # pragma: no cover - defensive
            return
        list_view.focus()


class _ProfileContextRequested(Message):
    """Message emitted when a list item is right-clicked."""

    def __init__(self, profile_name: str) -> None:
        super().__init__()
        self.profile_name = profile_name


__all__ = ["NavigationSidebar"]
