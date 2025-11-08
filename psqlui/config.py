"""App configuration loading helpers."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

CONFIG_FILE = Path.home() / ".config" / "psqlui" / "config.toml"


class AppConfig(BaseModel):
    """Shape of the application configuration file."""

    theme: str = "dark"
    telemetry_enabled: bool = False


def load_config() -> AppConfig:
    """Load configuration from disk; fall back to defaults if missing."""

    # Config parsing will be implemented later; for now return defaults.
    return AppConfig()
