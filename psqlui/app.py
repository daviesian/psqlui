"""Textual application entry point for psqlui."""

from __future__ import annotations

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, Static

from .config import AppConfig, load_config
from .plugins import PluginContext, PluginLoader
from .sqlintel import SqlIntelService, StaticMetadataProvider
from .widgets import QueryPad


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
        self._plugin_loader = self._create_plugin_loader()
        self._plugin_loader.load()

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

    def _create_plugin_loader(self) -> PluginLoader:
        ctx = PluginContext(app=self, sql_intel=self._sql_service, config=self._config)
        enabled = self._config.enabled_plugins()
        return PluginLoader(ctx, enabled_plugins=enabled)

    async def _shutdown(self) -> None:
        await self._plugin_loader.shutdown()
        await super()._shutdown()


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
