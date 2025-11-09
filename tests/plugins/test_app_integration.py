"""App-level tests for plugin loading."""

from __future__ import annotations

import importlib.metadata as metadata
from pathlib import Path

import pytest

from examples.plugins.hello_world import HelloWorldPlugin
from psqlui.app import PsqluiApp
from psqlui.config import AppConfig, ConnectionProfileConfig
from psqlui.connections import ConnectionBackendError
from psqlui.plugins import MetadataHookCapability
from psqlui.plugins.providers import PluginCommandProvider, PluginToggleProvider
from psqlui.providers import ProfileSwitchProvider, SessionRefreshProvider

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
async def test_profile_switch_provider_updates_active_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("psqlui.config.CONFIG_FILE", config_path)
    profiles = [
        ConnectionProfileConfig(name="Local Demo", metadata_key="demo"),
        ConnectionProfileConfig(name="Analytics Replica", metadata_key="analytics"),
    ]
    config = AppConfig(profiles=profiles, active_profile="Local Demo")
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        provider = ProfileSwitchProvider(_DummyScreen(app))
        hits = [hit async for hit in provider.discover()]
        target = next(hit for hit in hits if "Analytics Replica" in (hit.display or ""))
        await target.command()
        assert app.session_manager.active_profile_name == "Analytics Replica"
        assert 'active_profile = "Analytics Replica"' in config_path.read_text()
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_session_refresh_provider_triggers_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig()
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        called = False
        original = app.session_manager.refresh_active_profile

        def _fake_refresh() -> None:
            nonlocal called
            called = True
            original()

        app.session_manager.refresh_active_profile = _fake_refresh  # type: ignore[assignment]
        provider = SessionRefreshProvider(_DummyScreen(app))
        hits = [hit async for hit in provider.discover()]
        assert hits
        await hits[0].command()
        assert called
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_refresh_action_invokes_session_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig()
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        called = False
        original = app.session_manager.refresh_active_profile

        def _fake_refresh() -> None:
            nonlocal called
            called = True
            original()

        app.session_manager.refresh_active_profile = _fake_refresh  # type: ignore[assignment]
        app.action_refresh()
        assert called
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_app_persists_sidebar_width(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("psqlui.config.CONFIG_FILE", config_path)
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: AppConfig())

    app = PsqluiApp()

    try:
        app.remember_sidebar_width(44)
    finally:
        await app.plugin_loader.shutdown()

    content = config_path.read_text()
    assert "sidebar_width = 44" in content


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


@pytest.mark.anyio
async def test_metadata_hooks_receive_session_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    hook_entry = metadata.EntryPoint(
        name="hook-plugin",
        value="tests.plugins.test_app_integration:_HookPlugin",
        group="psqlui.plugins",
    )
    monkeypatch.setattr(metadata, "entry_points", lambda: metadata.EntryPoints((hook_entry,)))
    config = AppConfig(plugins={"hook-plugin": True})
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        manager = app.session_manager
        manager.refresh_active_profile()
        assert app.plugin_loader.loaded
        descriptor = app.plugin_loader.loaded[0].descriptor
        assert getattr(descriptor, "events")
        assert descriptor.events[-1].profile.name == manager.state.profile.name  # type: ignore[union-attr]
    finally:
        await app.plugin_loader.shutdown()


@pytest.mark.anyio
async def test_fallback_triggers_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("psqlui.session.AsyncpgConnectionBackend", _AlwaysFailBackend)
    config = AppConfig()
    monkeypatch.setattr("psqlui.app._load_app_config", lambda: config)

    app = PsqluiApp()

    try:
        state = app.session_manager.state
        assert state is not None and state.using_fallback is True
        assert app._pending_notifications  # type: ignore[attr-defined]
        message, severity = app._pending_notifications[0]
        assert severity == "warning"
        assert state.profile.name in message
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


class _HookPlugin:
    """Test plugin emitting metadata hook events."""

    name = "hook-plugin"
    version = "0.0.1"
    min_core = "0.1.0"

    def __init__(self) -> None:
        self.events: list[object] = []

    def register(self, ctx):  # type: ignore[override]
        def _handle(state):
            self.events.append(state)

        return [
            MetadataHookCapability(
                name="hook-plugin.metadata",
                handler=_handle,
            )
        ]

    async def on_shutdown(self) -> None:  # pragma: no cover - nothing to clean
        return None


class _AlwaysFailBackend:
    """Backend stub that always raises to force fallback path."""

    def __init__(self) -> None:
        self._listeners: set[object] = set()

    def connect(self, profile):  # type: ignore[no-untyped-def]
        raise ConnectionBackendError("connect failed")

    def refresh(self, profile):  # type: ignore[no-untyped-def]
        raise ConnectionBackendError("refresh failed")

    def subscribe(self, listener):  # type: ignore[no-untyped-def]
        self._listeners.add(listener)

        def _unsubscribe() -> None:
            self._listeners.discard(listener)

        return _unsubscribe
