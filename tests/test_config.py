"""Tests for AppConfig helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from psqlui import config as config_module
from psqlui.config import AppConfig, ConnectionProfileConfig, LayoutState, load_config, save_config


def test_enabled_plugins_returns_none_when_unset() -> None:
    config = AppConfig()

    assert config.enabled_plugins() is None


def test_enabled_plugins_returns_truthy_names() -> None:
    config = AppConfig(plugins={"hello-world": True, "unused": False})

    assert config.enabled_plugins() == {"hello-world"}


def test_enabled_plugins_can_disable_all() -> None:
    config = AppConfig(plugins={"hello-world": False})

    assert config.enabled_plugins() is None
    assert config.disabled_plugins() == {"hello-world"}


def test_load_config_returns_defaults_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "config.toml")

    result = load_config()

    assert result == AppConfig()


def test_load_config_reads_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
theme = "light"
telemetry_enabled = true
active_profile = "Local Demo"

[plugins]
hello-world = true
other = false

[[profiles]]
name = "Local Demo"
host = "localhost"
database = "postgres"
user = "postgres"
metadata_key = "demo"

[layout]
sidebar_width = 30
"""
    )
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_path)

    result = load_config()

    assert result.theme == "light"
    assert result.telemetry_enabled is True
    assert result.plugins == {"hello-world": True, "other": False}
    assert result.active_profile == "Local Demo"
    assert result.profiles[0].name == "Local Demo"
    assert result.layout.sidebar_width == 30


def test_load_config_handles_toml_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("theme = [unterminated")
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_path)

    result = load_config()

    assert result == AppConfig()


def test_with_plugin_enabled_toggles_flags() -> None:
    config = AppConfig(plugins={})

    updated = config.with_plugin_enabled("hello-world", False)
    assert updated.disabled_plugins() == {"hello-world"}
    restored = updated.with_plugin_enabled("hello-world", True)
    assert restored.disabled_plugins() == set()


def test_save_config_persists_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_path)

    save_config(
        AppConfig(
            theme="light",
            telemetry_enabled=True,
            plugins={"hello-world": False},
            profiles=[
                ConnectionProfileConfig(
                    name="Local Demo",
                    host="localhost",
                    database="postgres",
                    user="postgres",
                    metadata_key="demo",
                )
            ],
            active_profile="Local Demo",
            layout=LayoutState(sidebar_width=32),
        )
    )

    content = config_path.read_text()
    assert 'theme = "light"' in content
    assert "telemetry_enabled = true" in content
    assert 'active_profile = "Local Demo"' in content
    assert "[layout]" in content
    assert "sidebar_width = 32" in content
    assert "[[profiles]]" in content
    assert 'name = "Local Demo"' in content
    assert "[plugins]" in content
    assert "hello-world = false" in content


def test_with_active_profile_updates_field() -> None:
    config = AppConfig()

    updated = config.with_active_profile("Local Demo")

    assert updated.active_profile == "Local Demo"


def test_with_layout_updates_state() -> None:
    config = AppConfig()

    updated = config.with_layout(sidebar_width=40)

    assert updated.layout.sidebar_width == 40
