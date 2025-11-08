"""App configuration loading helpers."""

from __future__ import annotations

from pathlib import Path

import tomllib

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

    try:
        data = _read_config_file()
    except FileNotFoundError:
        return AppConfig()
    except (tomllib.TOMLDecodeError, OSError):
        return AppConfig()

    return AppConfig(
        theme=data.get("theme", AppConfig.model_fields["theme"].default),
        telemetry_enabled=data.get(
            "telemetry_enabled", AppConfig.model_fields["telemetry_enabled"].default
        ),
        plugins=data.get("plugins", {}),
    )


def _read_config_file() -> dict[str, object]:
    with CONFIG_FILE.open("rb") as handle:
        raw = tomllib.load(handle)
    data: dict[str, object] = {}
    if isinstance(raw, dict):
        theme = raw.get("theme")
        if isinstance(theme, str):
            data["theme"] = theme
        telemetry = raw.get("telemetry_enabled")
        if isinstance(telemetry, bool):
            data["telemetry_enabled"] = telemetry
        plugins = raw.get("plugins")
        if isinstance(plugins, dict):
            parsed_plugins: dict[str, bool] = {}
            for name, enabled in plugins.items():
                parsed_plugins[str(name)] = bool(enabled)
            data["plugins"] = parsed_plugins
    return data
