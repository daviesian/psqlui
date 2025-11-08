"""Tests for AppConfig helpers."""

from __future__ import annotations

from pathlib import Path

from psqlui import config as config_module
from psqlui.config import AppConfig, load_config


def test_enabled_plugins_returns_none_when_unset() -> None:
    config = AppConfig()

    assert config.enabled_plugins() is None


def test_enabled_plugins_returns_truthy_names() -> None:
    config = AppConfig(plugins={"hello-world": True, "unused": False})

    assert config.enabled_plugins() == {"hello-world"}


def test_enabled_plugins_can_disable_all() -> None:
    config = AppConfig(plugins={"hello-world": False})

    assert config.enabled_plugins() == set()


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

[plugins]
hello-world = true
other = false
"""
    )
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_path)

    result = load_config()

    assert result.theme == "light"
    assert result.telemetry_enabled is True
    assert result.plugins == {"hello-world": True, "other": False}


def test_load_config_handles_toml_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("theme = [unterminated")
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_path)

    result = load_config()

    assert result == AppConfig()
