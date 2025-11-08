"""Textual application entry point for psqlui."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Footer, Header, Static

from .config import AppConfig, load_config, save_config
from .plugins import (
    CommandCapability,
    PaneCapability,
    PluginCommandProvider,
    PluginCommandRegistry,
    PluginContext,
    PluginLoader,
    PluginToggleProvider,
)
from .providers import ProfileSwitchProvider, SessionRefreshProvider
from .session import SessionManager
from .sqlintel import SqlIntelService
from .widgets import NavigationSidebar, QueryPad, StatusBar

try:
    from examples.plugins.hello_world import HelloWorldPlugin
except ImportError:  # pragma: no cover - optional dev helper
    HelloWorldPlugin = None


class Hero(Static):
    """Splash widget shown in the placeholder UI."""

    DEFAULT_CSS = """
    Hero {
        content-align: center middle;
        height: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__("PSQL UI coming soon — press Ctrl+C to exit.")


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
        self._command_registry = PluginCommandRegistry()
        self._plugin_context: PluginContext | None = None
        self._nav_sidebar: NavigationSidebar | None = None
        self._query_pad: QueryPad | None = None
        self._plugin_loader = self._create_plugin_loader()
        self._plugin_loader.load()
        self._register_plugin_commands()
        self._pane_widgets: list[Widget] = self._mount_plugin_panes()

    def compose(self) -> ComposeResult:
        """Compose the root layout."""

        yield Header(show_clock=True)
        nav_sidebar = NavigationSidebar(self._session_manager)
        sidebar_width = self._config.layout.sidebar_width
        if sidebar_width:
            nav_sidebar.styles.width = sidebar_width
            nav_sidebar.styles.min_width = sidebar_width
            nav_sidebar.styles.max_width = sidebar_width
        self._nav_sidebar = nav_sidebar
        query_pad = QueryPad(
            self._sql_service,
            initial_metadata=self._session_manager.metadata_snapshot,
            session_manager=self._session_manager,
        )
        self._query_pad = query_pad
        main_column = Container(
            Hero(),
            query_pad,
            id="main-column",
        )
        sidebar_children = self._pane_widgets or [Static("No plugin panes active", id="plugin-pane-empty")]
        sidebar = Vertical(*sidebar_children, id="plugin-sidebar")
        yield Horizontal(nav_sidebar, main_column, sidebar, id="content")
        yield StatusBar(self._session_manager)
        yield Footer()

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


def main() -> None:
    """Invoke the Textual application."""

    PsqluiApp().run()


if __name__ == "__main__":
    main()
