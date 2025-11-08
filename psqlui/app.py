"""Textual application entry point for psqlui."""

from __future__ import annotations

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, Static

from .config import AppConfig, load_config
from .plugins import (
    CommandCapability,
    PluginCommandProvider,
    PluginCommandRegistry,
    PluginContext,
    PluginLoader,
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

    COMMANDS = App.COMMANDS | {PluginCommandProvider}
    CSS = """
    Screen {
        layout: vertical;
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
        self._plugin_loader = self._create_plugin_loader()
        self._plugin_loader.load()
        self._register_plugin_commands()

    def compose(self) -> ComposeResult:
        """Compose the root layout."""

        yield Header(show_clock=True)
        yield Container(
            Hero(),
            QueryPad(
                self._sql_service,
                initial_metadata=DEMO_METADATA[0],
                metadata_presets=DEMO_METADATA,
            ),
        )
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

    def _create_plugin_loader(self) -> PluginLoader:
        ctx = PluginContext(app=self, sql_intel=self._sql_service, config=self._config)
        enabled = self._config.enabled_plugins()
        builtin_plugins = [HelloWorldPlugin] if HelloWorldPlugin is not None else None
        return PluginLoader(ctx, enabled_plugins=enabled, builtin_plugins=builtin_plugins)

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
