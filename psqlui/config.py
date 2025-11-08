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

    def plugin_filters(self) -> tuple[set[str] | None, set[str]]:
        """Return allow/block lists for plugin enablement."""

        allowed = {name for name, flag in self.plugins.items() if flag}
        disabled = {name for name, flag in self.plugins.items() if not flag}
        allowlist: set[str] | None = allowed or None
        return allowlist, disabled

    def enabled_plugins(self) -> set[str] | None:
        """Maintain compatibility with legacy loader API."""

        allowlist, _ = self.plugin_filters()
        return allowlist

    def disabled_plugins(self) -> set[str]:
        """Plugins explicitly disabled in config."""

        _, disabled = self.plugin_filters()
        return disabled

    def is_plugin_enabled(self, name: str) -> bool:
        allowlist, disabled = self.plugin_filters()
        if allowlist is not None:
            return name in allowlist
        return name not in disabled

    def with_plugin_enabled(self, name: str, enabled: bool) -> AppConfig:
        """Return a copy with the given plugin flag updated."""

        plugins = dict(self.plugins)
        if enabled:
            plugins.pop(name, None)
        else:
            plugins[name] = False
        return self.model_copy(update={"plugins": plugins})


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


def save_config(config: AppConfig) -> None:
    """Persist configuration to disk."""

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        f'theme = "{config.theme}"',
        f"telemetry_enabled = {str(config.telemetry_enabled).lower()}",
    ]
    if config.plugins:
        lines.append("")
        lines.append("[plugins]")
        for name in sorted(config.plugins):
            flag = "true" if config.plugins[name] else "false"
            lines.append(f"{name} = {flag}")
    CONFIG_FILE.write_text("\n".join(lines) + "\n")


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
