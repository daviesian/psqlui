"""App-level tests for plugin loading."""

from __future__ import annotations

import importlib.metadata as metadata
from pathlib import Path

import pytest

from examples.plugins.hello_world import HelloWorldPlugin
from psqlui.app import PsqluiApp
from psqlui.config import AppConfig
from psqlui.plugins.providers import PluginCommandProvider, PluginToggleProvider

ENTRY_POINT = metadata.EntryPoint(
    name="hello-world",
    value="examples.plugins.hello_world:HelloWorldPlugin",
    group="psqlui.plugins",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def fake_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    def _entry_points() -> metadata.EntryPoints:
        return metadata.EntryPoints((ENTRY_POINT,))

    monkeypatch.setattr(metadata, "entry_points", _entry_points)


@pytest.mark.anyio
async def test_app_loads_enabled_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig(plugins={HelloWorldPlugin.name: True})
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        assert app.plugin_loader.loaded
        assert app.command_registry.list_commands()
        assert any(widget.id == "hello-pane" for widget in app.plugin_panes)
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_app_initializes_session_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig()
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        assert app.session_manager.state is not None
        assert app.session_manager.metadata_snapshot
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_app_respects_disabled_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig(plugins={HelloWorldPlugin.name: False})
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        assert not app.plugin_loader.loaded
        assert app.command_registry.list_commands() == []
        assert app.plugin_panes == ()
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_command_registry_executes_plugin_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig(plugins={HelloWorldPlugin.name: True})
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        descriptor = app.plugin_loader.loaded[0].descriptor
        command = app.command_registry.list_commands()[0]
        assert descriptor.executions == 0
        await app.command_registry.execute(command.name)
        assert descriptor.executions == 1
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_plugin_command_provider_surfaces_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig(plugins={HelloWorldPlugin.name: True})
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        provider = PluginCommandProvider(_DummyScreen(app))
        hits = [hit async for hit in provider.search("hello")]
        assert hits
        descriptor = app.plugin_loader.loaded[0].descriptor
        assert descriptor.executions == 0
        await hits[0].command()
        assert descriptor.executions == 1
    finally:
        await app.plugin_loader.shutdown()
class _DummyScreen:
    """Minimal stub so providers can reference an app without a running screen stack."""

    def __init__(self, app: PsqluiApp) -> None:
        self.app = app
        self.focused = None


@pytest.mark.anyio
async def test_toggle_plugin_updates_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("psqlui.config.CONFIG_FILE", config_path)
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: AppConfig())

    app = PsqluiApp()

    try:
        app.toggle_plugin("hello-world", False)
        assert "hello-world = false" in config_path.read_text()
        assert not app.is_plugin_enabled("hello-world")
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_plugin_toggle_provider_creates_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("psqlui.config.CONFIG_FILE", config_path)
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: AppConfig())

    app = PsqluiApp()

    try:
        provider = PluginToggleProvider(_DummyScreen(app))
        hits = [hit async for hit in provider.discover()]
        assert any("Disable plugin" in (hit.text or hit.display) for hit in hits)
        await hits[0].command()
        assert config_path.exists()
    finally:
        await app.plugin_loader.shutdown()
