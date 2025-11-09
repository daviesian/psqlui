"""Composite widget providing a resizable navigation sidebar."""

from __future__ import annotations

from typing import Callable

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from psqlui.session import SessionManager

from .navigation_sidebar import NavigationSidebar

MIN_WIDTH = 18
MAX_WIDTH = 64


class SidebarPanel(Container):
    """Wraps the navigation sidebar with a draggable resize handle."""

    DEFAULT_CSS = """
    SidebarPanel {
        layout: horizontal;
        height: 1fr;
    }

    SidebarResizeHandle {
        width: 2;
        min-width: 2;
        height: 100%;
        min-height: 100%;
        background: $surface-darken-2;
        color: $text-muted;
        transition: background 120ms, color 120ms;
    }

    SidebarResizeHandle.hover {
        background: $surface-darken-1;
        color: $text;
    }

    SidebarResizeHandle.dragging,
    SidebarPanel.resizing SidebarResizeHandle {
        background: $primary;
        color: $text;
    }
    """

    def __init__(
        self,
        session_manager: SessionManager,
        *,
        initial_width: int | None = None,
        on_width_change: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(id="sidebar-panel")
        self.sidebar = NavigationSidebar(session_manager)
        self._on_width_change = on_width_change or (lambda _: None)
        self._width = initial_width or 28
        self._resizing = False
        self._start_x = 0
        self._start_width = self._width
        self.styles.flex = "0 0 auto"

    @property
    def resizing(self) -> bool:
        return self._resizing

    def compose(self) -> ComposeResult:
        self._apply_width(self._width)
        yield self.sidebar
        yield SidebarResizeHandle(self)

    def begin_resize(self, screen_x: int) -> None:
        self._resizing = True
        self.set_class(True, "resizing")
        self._start_x = screen_x
        self._start_width = self._width

    def update_resize(self, screen_x: int) -> None:
        if not self._resizing:
            return
        delta = screen_x - self._start_x
        new_width = max(MIN_WIDTH, min(MAX_WIDTH, self._start_width + delta))
        self._apply_width(new_width)

    def end_resize(self) -> None:
        if not self._resizing:
            return
        self._resizing = False
        self.set_class(False, "resizing")
        self._on_width_change(int(self._width))

    def _apply_width(self, width: int) -> None:
        self._width = width
        self.sidebar.styles.width = width
        self.sidebar.styles.min_width = width
        self.sidebar.styles.max_width = width
        self.styles.width = width + 2


class SidebarResizeHandle(Static):
    """Draggable handle that resizes the sidebar panel."""

    DEFAULT_CSS = """
    SidebarResizeHandle {
        dock: right;
        content-align: center middle;
        text-style: bold;
    }
    """

    def __init__(self, panel: SidebarPanel) -> None:
        super().__init__("||", id="sidebar-resize-handle")
        self._panel = panel

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.capture_mouse()
        self._panel.begin_resize(event.screen_x)
        self.set_class(True, "dragging")

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._panel.resizing:
            self._panel.update_resize(event.screen_x)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        self.release_mouse()
        self._panel.end_resize()
        self.set_class(False, "dragging")

    def on_mouse_enter(self, event: events.MouseEnter) -> None:  # pragma: no cover - UI affordance
        self.set_class(True, "hover")

    def on_mouse_leave(self, event: events.MouseLeave) -> None:  # pragma: no cover - UI affordance
        self.set_class(False, "hover")
        if not self._panel.resizing:
            self.set_class(False, "dragging")


__all__ = ["SidebarPanel"]
