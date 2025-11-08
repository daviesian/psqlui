"""Tests for the demo connection backend."""

from __future__ import annotations

from psqlui.connections import DemoConnectionBackend
from psqlui.session import ConnectionProfile


def test_backend_cycles_metadata_snapshots() -> None:
    backend = DemoConnectionBackend(
        {
            "demo": (
                {"public.accounts": ("id",)},
                {"public.accounts": ("id", "email")},
            )
        }
    )
    profile = ConnectionProfile(name="Local", metadata_key="demo")
    snapshots: list[tuple[str, ...]] = []

    event = backend.connect(profile)
    assert event.metadata["public.accounts"] == ("id",)

    backend.subscribe(lambda _, ev: snapshots.append(ev.metadata["public.accounts"]))
    backend.refresh(profile)

    assert snapshots[0] == ("id", "email")
