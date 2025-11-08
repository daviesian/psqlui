"""App configuration loading helpers."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

CONFIG_FILE = Path.home() / ".config" / "psqlui" / "config.toml"


class AppConfig(BaseModel):
    """Shape of the application configuration file."""

    theme: str = "dark"
    telemetry_enabled: bool = False
    plugins: dict[str, bool] = Field(default_factory=dict)

    def enabled_plugins(self) -> set[str] | None:
        """Return the configured allow-list or None to load everything."""

        if not self.plugins:
            return None
        enabled = {name for name, flag in self.plugins.items() if flag}
        if enabled:
            return enabled
        return set()


def load_config() -> AppConfig:
    """Load configuration from disk; fall back to defaults if missing."""

    # Config parsing will be implemented later; for now return defaults.
    return AppConfig()
