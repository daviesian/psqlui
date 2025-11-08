"""App-level tests for plugin loading."""

from __future__ import annotations

import importlib.metadata as metadata

import pytest

from examples.plugins.hello_world import HelloWorldPlugin
from psqlui.app import PsqluiApp
from psqlui.config import AppConfig

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
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_app_respects_disabled_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig(plugins={HelloWorldPlugin.name: False})
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        assert not app.plugin_loader.loaded
    finally:
        await app.plugin_loader.shutdown()
