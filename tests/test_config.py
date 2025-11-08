"""Tests for AppConfig helpers."""

from __future__ import annotations

from psqlui.config import AppConfig


def test_enabled_plugins_returns_none_when_unset() -> None:
    config = AppConfig()

    assert config.enabled_plugins() is None


def test_enabled_plugins_returns_truthy_names() -> None:
    config = AppConfig(plugins={"hello-world": True, "unused": False})

    assert config.enabled_plugins() == {"hello-world"}


def test_enabled_plugins_can_disable_all() -> None:
    config = AppConfig(plugins={"hello-world": False})

    assert config.enabled_plugins() == set()
