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

    initial = backend.connect(profile)
    assert initial["public.accounts"] == ("id",)

    backend.subscribe(lambda _, metadata: snapshots.append(metadata["public.accounts"]))
    backend.refresh(profile)

    assert snapshots[0] == ("id", "email")
