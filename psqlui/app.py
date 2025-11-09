"""Textual application entry point for psqlui."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Callable

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Footer, Header, Static

from .config import AppConfig, load_config, save_config
from .plugins import (
    CommandCapability,
    MetadataHookCapability,
    PaneCapability,
    PluginCommandProvider,
    PluginCommandRegistry,
    PluginContext,
    PluginLoader,
    PluginToggleProvider,
)
from .providers import ProfileSwitchProvider, SessionRefreshProvider
from .session import SessionManager, SessionState
from .sqlintel import SqlIntelService
from .widgets import NavigationSidebar, QueryPad, SidebarPanel, StatusBar

try:
    from examples.plugins.hello_world import HelloWorldPlugin
except ImportError:  # pragma: no cover - optional dev helper
    HelloWorldPlugin = None


LOG = logging.getLogger(__name__)


def _load_app_config() -> AppConfig:
    """Load configuration with a small wrapper for future overrides."""

    return load_config()


class PsqluiApp(App[None]):
    """Minimal Textual shell that will grow into the full TUI."""

    COMMANDS = App.COMMANDS | {PluginCommandProvider, PluginToggleProvider, ProfileSwitchProvider, SessionRefreshProvider}
    CSS = """
    Screen {
        layout: vertical;
    }
    #content {
        layout: horizontal;
        height: 1fr;
    }
    #main-column {
        layout: vertical;
        padding: 1 2;
        height: 1fr;
        border-left: solid $surface-darken-1;
        border-right: solid $surface-darken-1;
    }
    NavigationSidebar {
        width: 28;
        min-width: 22;
    }
    #plugin-sidebar {
        width: 32;
        min-width: 24;
        border-left: heavy $primary;
        padding: 1;
        height: 1fr;
    }
    #plugin-sidebar:empty {
        width: 0;
        min-width: 0;
        padding: 0;
        border: none;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+r", "refresh", "Refresh Metadata"),
        ("ctrl+p", "command_palette", "Command Palette"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._config = _load_app_config()
        self._sql_service = SqlIntelService()
        self._session_manager = SessionManager(self._sql_service, config=self._config)
        if self._session_manager.state:
            self._config = self._config.with_active_profile(self._session_manager.state.profile.name)
        self._session_unsubscribe: Callable[[], None] | None = None
        self._last_session_state: SessionState | None = None
        self._pending_notifications: list[tuple[str, str]] = []
        self._command_registry = PluginCommandRegistry()
        self._plugin_context: PluginContext | None = None
        self._nav_sidebar: NavigationSidebar | None = None
        self._query_pad: QueryPad | None = None
        self._metadata_hooks: list[MetadataHookCapability] = []
        self._plugin_loader = self._create_plugin_loader()
        self._plugin_loader.load()
        self._register_plugin_commands()
        self._metadata_hooks = self._collect_metadata_hooks()
        self._install_session_listener()
        self._pane_widgets: list[Widget] = self._mount_plugin_panes()

    def compose(self) -> ComposeResult:
        """Compose the root layout."""

        yield Header(show_clock=True)
        sidebar_panel = SidebarPanel(
            self._session_manager,
            initial_width=self._config.layout.sidebar_width,
            on_width_change=self.remember_sidebar_width,
        )
        self._nav_sidebar = sidebar_panel.sidebar
        query_pad = QueryPad(
            self._sql_service,
            initial_metadata=self._session_manager.metadata_snapshot,
            session_manager=self._session_manager,
        )
        self._query_pad = query_pad
        main_column = Container(query_pad, id="main-column")
        content_children: list[Widget] = [sidebar_panel, main_column]
        if self._pane_widgets:
            sidebar = Vertical(*self._pane_widgets, id="plugin-sidebar")
            content_children.append(sidebar)
        yield Horizontal(*content_children, id="content")
        yield StatusBar(self._session_manager)
        yield Footer()

    async def on_mount(self) -> None:
        self._flush_pending_notifications()

    def action_refresh(self) -> None:
        self._session_manager.refresh_active_profile()

    @property
    def plugin_loader(self) -> PluginLoader:
        """Expose the plugin loader for tests and future wiring."""

        return self._plugin_loader

    @property
    def command_registry(self) -> PluginCommandRegistry:
        """Return plugin command registry."""

        return self._command_registry

    @property
    def session_manager(self) -> SessionManager:
        """Expose the session manager for tests."""

        return self._session_manager

    @property
    def plugin_panes(self) -> tuple[Widget, ...]:
        """Expose mounted plugin pane widgets (testing helper)."""

        return tuple(self._pane_widgets)

    def available_plugins(self) -> tuple[str, ...]:
        """Names of discovered plugins."""

        return tuple(plugin.name for plugin in self._plugin_loader.discovered)

    def is_plugin_enabled(self, name: str) -> bool:
        return self._config.is_plugin_enabled(name)

    def toggle_plugin(self, name: str, enabled: bool) -> None:
        self._config = self._config.with_plugin_enabled(name, enabled)
        save_config(self._config)
        state = "enabled" if enabled else "disabled"
        self.notify(f"{name} {state}. Restart to apply.", severity="information")

    def switch_profile(self, name: str) -> None:
        """Activate the requested connection profile and persist the choice."""

        try:
            state = self._session_manager.connect(name)
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return
        self._config = self._config.with_active_profile(state.profile.name)
        save_config(self._config)
        self.notify(f"Switched to profile: {state.profile.name}", severity="information")

    def remember_sidebar_width(self, width: int) -> None:
        """Persist the sidebar width when it changes."""

        if self._config.layout.sidebar_width == width:
            return
        self._config = self._config.with_layout(sidebar_width=width)
        save_config(self._config)

    def _create_plugin_loader(self) -> PluginLoader:
        ctx = PluginContext(
            app=self,
            sql_intel=self._sql_service,
            metadata_cache=self._session_manager,
            config=self._config,
        )
        self._plugin_context = ctx
        allowlist, disabled = self._config.plugin_filters()
        builtin_plugins = [HelloWorldPlugin] if HelloWorldPlugin is not None else None
        return PluginLoader(
            ctx,
            enabled_plugins=allowlist,
            disabled_plugins=disabled,
            builtin_plugins=builtin_plugins,
        )

    async def _shutdown(self) -> None:
        if self._session_unsubscribe:
            self._session_unsubscribe()
            self._session_unsubscribe = None
        await self._plugin_loader.shutdown()
        await super()._shutdown()

    def _register_plugin_commands(self) -> None:
        commands: list[CommandCapability] = []
        for plugin in self._plugin_loader.loaded:
            for capability in plugin.capabilities:
                if isinstance(capability, CommandCapability):
                    commands.append(capability)
        if commands:
            self._command_registry.register_many(commands)

    def _collect_metadata_hooks(self) -> list[MetadataHookCapability]:
        hooks: list[MetadataHookCapability] = []
        for plugin in self._plugin_loader.loaded:
            for capability in plugin.capabilities:
                if isinstance(capability, MetadataHookCapability) and capability.handler is not None:
                    hooks.append(capability)
        return hooks

    def _mount_plugin_panes(self) -> list[Widget]:
        panes: list[Widget] = []
        context = self._plugin_context or PluginContext(app=self, sql_intel=self._sql_service, config=self._config)
        for plugin in self._plugin_loader.loaded:
            for capability in plugin.capabilities:
                if isinstance(capability, PaneCapability) and capability.mount is not None:
                    widget = capability.mount(context)
                    if isinstance(widget, Widget):
                        panes.append(widget)
        return panes

    def _install_session_listener(self) -> None:
        if self._session_unsubscribe:
            self._session_unsubscribe()
        self._session_unsubscribe = self._session_manager.subscribe(self._handle_session_state)

    def _handle_session_state(self, state: SessionState) -> None:
        self._dispatch_metadata_hooks(state)
        self._maybe_notify_state_change(state)
        self._last_session_state = state

    def _dispatch_metadata_hooks(self, state: SessionState) -> None:
        for capability in self._metadata_hooks:
            handler = capability.handler
            if handler is None:
                continue
            try:
                result = handler(state)
            except Exception:
                LOG.exception(
                    "Metadata hook failed",
                    extra={"hook": capability.name},
                )
                continue
            self._maybe_schedule_hook(result)

    def _maybe_schedule_hook(self, result: object) -> None:
        if result is None:
            return
        if inspect.isawaitable(result):
            try:
                asyncio.ensure_future(result)  # type: ignore[arg-type]
            except RuntimeError:
                asyncio.run(result)  # type: ignore[arg-type]

    def _maybe_notify_state_change(self, state: SessionState) -> None:
        previous = self._last_session_state
        if state.using_fallback and (not previous or not previous.using_fallback):
            reason = ""
            if state.last_error:
                reason = f" ({state.last_error.splitlines()[0][:120]})"
            self._safe_notify(
                f"{state.profile.name}: Primary backend unavailable, using demo fallback{reason}.",
                severity="warning",
            )
        elif previous and previous.using_fallback and not state.using_fallback:
            self._safe_notify(
                f"{state.profile.name}: Reconnected to primary backend.",
                severity="information",
            )

    def _safe_notify(self, message: str, *, severity: str = "information") -> None:
        if self.is_running:
            try:
                self.notify(message, severity=severity)
            except Exception:
                LOG.exception("Failed to display notification", extra={"message": message})
        else:
            self._pending_notifications.append((message, severity))

    def _flush_pending_notifications(self) -> None:
        if not self._pending_notifications:
            return
        pending = list(self._pending_notifications)
        self._pending_notifications.clear()
        for message, severity in pending:
            try:
                self.notify(message, severity=severity)
            except Exception:
                LOG.exception("Failed to display queued notification", extra={"message": message})


def main() -> None:
    """Invoke the Textual application."""

    PsqluiApp().run()


if __name__ == "__main__":
    main()
