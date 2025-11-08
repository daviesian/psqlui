"""Tests for the plugin loader prototype."""

from __future__ import annotations

import importlib.metadata as metadata

import pytest

from examples.plugins.hello_world import HelloWorldPlugin
from psqlui.plugins import CommandCapability, PaneCapability, PluginContext, PluginLoader

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
    """Force discovery to use the sample plugin."""

    def _entry_points() -> metadata.EntryPoints:
        return metadata.EntryPoints((ENTRY_POINT,))

    monkeypatch.setattr(metadata, "entry_points", _entry_points)


def test_discover_returns_plugin_metadata() -> None:
    loader = PluginLoader(PluginContext())

    discovered = loader.discover()

    assert discovered
    assert discovered[0].name == HelloWorldPlugin.name
    assert discovered[0].version == HelloWorldPlugin.version


def test_load_registers_capabilities_and_context() -> None:
    ctx = PluginContext(app="app")
    loader = PluginLoader(ctx)

    loaded = loader.load()

    assert loaded
    plugin = loaded[0]
    assert any(isinstance(cap, CommandCapability) for cap in plugin.capabilities)
    assert any(isinstance(cap, PaneCapability) for cap in plugin.capabilities)
    descriptor = plugin.descriptor
    assert isinstance(descriptor, HelloWorldPlugin)
    assert descriptor.last_context == ctx


def test_disabled_plugin_is_skipped() -> None:
    loader = PluginLoader(PluginContext(), enabled_plugins={"other"})

    loader.discover()
    loaded = loader.load()

    assert loaded == []


def test_incompatible_plugin_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(HelloWorldPlugin, "min_core", "9.9.9")
    loader = PluginLoader(PluginContext(), core_version="0.1.0")

    loaded = loader.load()

    assert loaded == []


@pytest.mark.anyio
async def test_shutdown_invokes_plugin_hook() -> None:
    loader = PluginLoader(PluginContext())
    loaded = loader.load()
    descriptor = loaded[0].descriptor

    assert not descriptor.shutdown_called
    await loader.shutdown()
    assert descriptor.shutdown_called


def test_builtin_plugin_is_discovered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(metadata, "entry_points", lambda: metadata.EntryPoints(()))
    loader = PluginLoader(PluginContext(), builtin_plugins=[HelloWorldPlugin])

    discovered = loader.discover()

    assert discovered
    assert discovered[0].name == HelloWorldPlugin.name
