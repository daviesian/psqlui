"""Tests for the session manager wiring."""

from __future__ import annotations

from datetime import datetime

import pytest

from psqlui.config import AppConfig, ConnectionProfileConfig
from psqlui.connections import ConnectionBackendError, DemoConnectionBackend
from psqlui.query import QueryResult
from psqlui.session import SessionManager


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _SqlIntelStub:
    def __init__(self) -> None:
        self.last_metadata: dict[str, tuple[str, ...]] | None = None

    def update_metadata(self, tables):  # type: ignore[no-untyped-def]
        self.last_metadata = dict(tables)


def test_session_manager_connects_first_profile_by_default() -> None:
    config = AppConfig()
    service = _SqlIntelStub()

    manager = SessionManager(service, config=config, backend=DemoConnectionBackend())

    assert manager.state is not None
    assert manager.state.connected is True
    assert manager.state.metadata
    assert manager.state.schemas
    assert manager.state.refreshed_at is not None
    assert manager.state.status
    assert manager.state.latency_ms is not None
    assert manager.state.backend_label == "Primary backend"
    assert manager.state.using_fallback is False
    assert manager.state.last_error is None
    assert service.last_metadata == dict(manager.state.metadata)


def test_session_manager_switches_profiles_and_notifies_listeners() -> None:
    profiles = [
        ConnectionProfileConfig(name="Local", metadata_key="demo"),
        ConnectionProfileConfig(name="Replica", metadata_key="analytics"),
    ]
    config = AppConfig(profiles=profiles, active_profile="Local")
    service = _SqlIntelStub()
    manager = SessionManager(service, config=config, backend=DemoConnectionBackend())
    seen: list[str] = []
    timestamps: list[datetime] = []

    def _listener(state):
        seen.append(state.profile.name)
        timestamps.append(state.refreshed_at)

    unsubscribe = manager.subscribe(_listener)
    assert timestamps
    manager.connect("Replica")

    assert seen[-1] == "Replica"
    assert manager.state is not None and manager.state.profile.name == "Replica"
    assert service.last_metadata == dict(manager.state.metadata)
    assert "analytics" in manager.state.schemas
    assert timestamps[-1] >= timestamps[0]
    assert manager.state.latency_ms is not None
    unsubscribe()


def test_session_manager_errors_on_missing_profile() -> None:
    config = AppConfig(profiles=[ConnectionProfileConfig(name="Only", metadata_key="demo")])
    service = _SqlIntelStub()
    manager = SessionManager(service, config=config, backend=DemoConnectionBackend())

    try:
        manager.connect("unknown")
    except ValueError as exc:
        assert "Profile 'unknown' not found" in str(exc)
    else:  # pragma: no cover - defensive, should not happen
        assert False, "Expected ValueError for missing profile"


def test_refresh_cycle_updates_metadata() -> None:
    backend = DemoConnectionBackend(
        {
            "demo": (
                {"public.accounts": ("id",)},
                {"public.accounts": ("id", "email")},
            )
        }
    )
    config = AppConfig(profiles=[ConnectionProfileConfig(name="Local", metadata_key="demo")], active_profile="Local")
    service = _SqlIntelStub()
    manager = SessionManager(service, config=config, backend=backend)
    lengths: list[int] = []

    manager.subscribe(lambda state: lengths.append(len(state.metadata["public.accounts"])))
    initial_timestamp = manager.state.refreshed_at
    manager.refresh_active_profile()

    assert lengths[-1] == 2
    assert manager.state.refreshed_at > initial_timestamp
    assert manager.state.status


def test_refresh_profile_switches_and_refreshes_non_active_profile() -> None:
    backend = DemoConnectionBackend(
        {
            "demo": (
                {"public.accounts": ("id",)},
                {"public.accounts": ("id", "email")},
            ),
            "analytics": (
                {"analytics.events": ("id",)},
                {"analytics.events": ("id", "payload")},
            ),
        }
    )
    profiles = [
        ConnectionProfileConfig(name="Local", metadata_key="demo"),
        ConnectionProfileConfig(name="Replica", metadata_key="analytics"),
    ]
    config = AppConfig(profiles=profiles, active_profile="Local")
    service = _SqlIntelStub()
    manager = SessionManager(service, config=config, backend=backend)

    manager.refresh_profile("Replica")

    assert manager.state is not None
    assert manager.state.profile.name == "Replica"
    assert manager.state.metadata["analytics.events"] == ("id", "payload")
    assert service.last_metadata == dict(manager.state.metadata)
    assert "analytics" in manager.state.schemas


def test_session_manager_falls_back_when_primary_backend_fails() -> None:
    class _FailingBackend(DemoConnectionBackend):
        def connect(self, profile):  # type: ignore[override]
            raise ConnectionBackendError("boom")

        def refresh(self, profile):  # type: ignore[override]
            raise ConnectionBackendError("boom")

    profiles = [ConnectionProfileConfig(name="Local", metadata_key="demo")]
    config = AppConfig(profiles=profiles, active_profile="Local")
    service = _SqlIntelStub()
    manager = SessionManager(
        service,
        config=config,
        backend=_FailingBackend(),
        fallback_backend=DemoConnectionBackend(
            {
                "demo": (
                    {"public.accounts": ("id",)},
                    {"public.accounts": ("id", "email")},
                )
            }
        ),
    )

    assert manager.state is not None
    assert manager.state.metadata["public.accounts"] == ("id",)
    assert "public" in manager.state.schemas
    assert manager.state.using_fallback is True
    assert manager.state.backend_label == "Demo fallback"
    assert manager.state.last_error and "boom" in manager.state.last_error
    manager.refresh_active_profile()
    assert manager.state.metadata["public.accounts"] == ("id", "email")
    assert manager.state.using_fallback is True
    assert manager.state.last_error and "boom" in manager.state.last_error


def test_refresh_failure_switches_to_demo_and_records_error() -> None:
    class _FlakyBackend(DemoConnectionBackend):
        def refresh(self, profile):  # type: ignore[override]
            raise ConnectionBackendError("refresh failed")

    profiles = [ConnectionProfileConfig(name="Local", metadata_key="demo")]
    config = AppConfig(profiles=profiles, active_profile="Local")
    service = _SqlIntelStub()
    primary = _FlakyBackend(
        {
            "demo": (
                {"public.accounts": ("id",)},
            )
        }
    )
    fallback = DemoConnectionBackend(
        {
            "demo": (
                {"public.accounts": ("id", "email", "status")},
            )
        }
    )
    manager = SessionManager(service, config=config, backend=primary, fallback_backend=fallback)

    assert manager.state is not None
    assert manager.state.using_fallback is False
    manager.refresh_active_profile()
    assert manager.state.using_fallback is True
    assert manager.state.metadata["public.accounts"] == ("id", "email", "status")
    assert manager.state.last_error and "refresh failed" in manager.state.last_error


@pytest.mark.anyio
async def test_run_query_uses_primary_executor() -> None:
    config = AppConfig(profiles=[ConnectionProfileConfig(name="Local", metadata_key="demo")], active_profile="Local")
    service = _SqlIntelStub()
    primary_executor = _QueryStub()
    fallback_executor = _QueryStub(status="Fallback")
    manager = SessionManager(
        service,
        config=config,
        backend=DemoConnectionBackend(),
        query_executor=primary_executor,
        fallback_query_executor=fallback_executor,
    )

    result = await manager.run_query("SELECT 1")

    assert result.status == "OK"
    assert primary_executor.calls == ["SELECT 1"]
    assert not fallback_executor.calls


@pytest.mark.anyio
async def test_run_query_uses_fallback_executor_when_demo_active() -> None:
    class _FailingBackend(DemoConnectionBackend):
        def connect(self, profile):  # type: ignore[override]
            raise ConnectionBackendError("down")

    config = AppConfig(profiles=[ConnectionProfileConfig(name="Local", metadata_key="demo")], active_profile="Local")
    service = _SqlIntelStub()
    primary_executor = _QueryStub()
    fallback_executor = _QueryStub(status="Fallback demo")
    manager = SessionManager(
        service,
        config=config,
        backend=_FailingBackend(),
        fallback_backend=DemoConnectionBackend(),
        query_executor=primary_executor,
        fallback_query_executor=fallback_executor,
    )

    assert manager.state is not None and manager.state.using_fallback is True
    result = await manager.run_query("SELECT * FROM demo")

    assert result.status == "Fallback demo"
    assert fallback_executor.calls == ["SELECT * FROM demo"]
    assert not primary_executor.calls
class _QueryStub:
    def __init__(self, status: str = "OK") -> None:
        self.calls: list[str] = []
        self.result = QueryResult(columns=("id",), rows=((1,),), status=status, elapsed_ms=1, row_count=1)

    async def execute(self, profile, sql):  # type: ignore[no-untyped-def]
        self.calls.append(sql)
        return self.result
