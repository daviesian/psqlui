"""Tests for the session manager wiring."""

from __future__ import annotations

from psqlui.config import AppConfig, ConnectionProfileConfig
from psqlui.session import DEFAULT_METADATA_PRESETS, SessionManager


class _SqlIntelStub:
    def __init__(self) -> None:
        self.last_metadata: dict[str, tuple[str, ...]] | None = None

    def update_metadata(self, tables):  # type: ignore[no-untyped-def]
        self.last_metadata = dict(tables)


def test_session_manager_connects_first_profile_by_default() -> None:
    config = AppConfig()
    service = _SqlIntelStub()

    manager = SessionManager(service, config=config, metadata_presets=DEFAULT_METADATA_PRESETS)

    assert manager.state is not None
    assert manager.state.connected is True
    assert manager.state.metadata
    assert service.last_metadata == dict(manager.state.metadata)


def test_session_manager_switches_profiles_and_notifies_listeners() -> None:
    profiles = [
        ConnectionProfileConfig(name="Local", metadata_key="demo"),
        ConnectionProfileConfig(name="Replica", metadata_key="analytics"),
    ]
    config = AppConfig(profiles=profiles, active_profile="Local")
    service = _SqlIntelStub()
    manager = SessionManager(service, config=config, metadata_presets=DEFAULT_METADATA_PRESETS)
    seen: list[str] = []

    unsubscribe = manager.subscribe(lambda state: seen.append(state.profile.name))
    manager.connect("Replica")

    assert seen[-1] == "Replica"
    assert manager.state is not None and manager.state.profile.name == "Replica"
    assert service.last_metadata == dict(manager.state.metadata)
    unsubscribe()


def test_session_manager_errors_on_missing_profile() -> None:
    config = AppConfig(profiles=[ConnectionProfileConfig(name="Only", metadata_key="demo")])
    service = _SqlIntelStub()
    manager = SessionManager(service, config=config, metadata_presets=DEFAULT_METADATA_PRESETS)

    try:
        manager.connect("unknown")
    except ValueError as exc:
        assert "Profile 'unknown' not found" in str(exc)
    else:  # pragma: no cover - defensive, should not happen
        assert False, "Expected ValueError for missing profile"
