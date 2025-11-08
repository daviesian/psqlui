"""Textual application entry point for psqlui."""

from __future__ import annotations

from textual import on
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
from .sqlintel import SqlIntelService, StaticMetadataProvider
from .widgets import QueryPad

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

    COMMANDS = App.COMMANDS | {PluginCommandProvider, PluginToggleProvider}
    CSS = """
    Screen {
        layout: vertical;
    }
    #content {
        layout: horizontal;
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
        ("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._config = _load_app_config()
        sample_metadata = StaticMetadataProvider(DEMO_METADATA[0])
        self._sql_service = SqlIntelService(metadata_provider=sample_metadata)
        self._command_registry = PluginCommandRegistry()
        self._plugin_context: PluginContext | None = None
        self._plugin_loader = self._create_plugin_loader()
        self._plugin_loader.load()
        self._register_plugin_commands()
        self._pane_widgets: list[Widget] = self._mount_plugin_panes()

    def compose(self) -> ComposeResult:
        """Compose the root layout."""

        yield Header(show_clock=True)
        main_column = Container(
            Hero(),
            QueryPad(
                self._sql_service,
                initial_metadata=DEMO_METADATA[0],
                metadata_presets=DEMO_METADATA,
            ),
        )
        sidebar_children = self._pane_widgets or [Static("No plugin panes active", id="plugin-pane-empty")]
        sidebar = Vertical(*sidebar_children, id="plugin-sidebar")
        yield Horizontal(main_column, sidebar, id="content")
        yield Footer()

    @on("refresh")
    def _handle_refresh(self) -> None:
        self.bell()

    @property
    def plugin_loader(self) -> PluginLoader:
        """Expose the plugin loader for tests and future wiring."""

        return self._plugin_loader

    @property
    def command_registry(self) -> PluginCommandRegistry:
        """Return plugin command registry."""

        return self._command_registry

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

    def _create_plugin_loader(self) -> PluginLoader:
        ctx = PluginContext(app=self, sql_intel=self._sql_service, config=self._config)
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
DEMO_METADATA = [
    {
        "public.accounts": ("id", "email", "last_login"),
        "public.orders": ("id", "account_id", "total"),
        "public.payments": ("id", "order_id", "amount"),
    },
    {
        "analytics.sessions": ("id", "user_id", "started_at", "device"),
        "analytics.events": ("id", "session_id", "name", "payload"),
    },
]
