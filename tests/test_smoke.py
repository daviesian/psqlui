"""Smoke tests for the initial package skeleton."""

from psqlui import __version__


def test_version_string() -> None:
    assert __version__ == "0.1.0"
