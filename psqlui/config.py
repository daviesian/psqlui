"""App configuration loading helpers."""

from __future__ import annotations

from pathlib import Path

import tomllib

from typing import Mapping, Sequence

from pydantic import BaseModel, Field

CONFIG_FILE = Path.home() / ".config" / "psqlui" / "config.toml"


class LayoutState(BaseModel):
    """Persisted layout hints for the TUI."""

    sidebar_width: int | None = None


class ConnectionProfileConfig(BaseModel):
    """Connection profile configuration stored in config.toml."""

    name: str
    dsn: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    user: str | None = None
    metadata_key: str | None = None
    metadata: Mapping[str, Sequence[str]] | None = None


class AppConfig(BaseModel):
    """Shape of the application configuration file."""

    theme: str = "dark"
    telemetry_enabled: bool = False
    plugins: dict[str, bool] = Field(default_factory=dict)
    profiles: list[ConnectionProfileConfig] = Field(default_factory=lambda: list(_default_profiles()))
    active_profile: str | None = None
    layout: LayoutState = Field(default_factory=LayoutState)

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

    def with_active_profile(self, name: str) -> AppConfig:
        """Return a copy with the active profile updated."""

        return self.model_copy(update={"active_profile": name})

    def with_layout(self, **updates: object) -> AppConfig:
        """Return a copy with layout state changes applied."""

        layout = self.layout.model_copy(update=updates)
        return self.model_copy(update={"layout": layout})


def load_config() -> AppConfig:
    """Load configuration from disk; fall back to defaults if missing."""

    try:
        data = _read_config_file()
    except FileNotFoundError:
        return AppConfig()
    except (tomllib.TOMLDecodeError, OSError):
        return AppConfig()

    profiles_data = data.get("profiles")
    profiles: list[ConnectionProfileConfig] | None = None
    if isinstance(profiles_data, list):
        profiles = [
            ConnectionProfileConfig(**profile)
            for profile in profiles_data  # type: ignore[list-item]
            if isinstance(profile, dict)
        ]

    return AppConfig(
        theme=data.get("theme", AppConfig.model_fields["theme"].default),
        telemetry_enabled=data.get(
            "telemetry_enabled", AppConfig.model_fields["telemetry_enabled"].default
        ),
        plugins=data.get("plugins", {}),
        profiles=profiles if profiles is not None else list(_default_profiles()),
        active_profile=data.get("active_profile"),
        layout=data.get("layout", LayoutState()),
    )


def save_config(config: AppConfig) -> None:
    """Persist configuration to disk."""

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        f'theme = "{config.theme}"',
        f"telemetry_enabled = {str(config.telemetry_enabled).lower()}",
    ]
    if config.active_profile:
        lines.append(f'active_profile = "{config.active_profile}"')
    if config.layout.sidebar_width is not None:
        lines.append("")
        lines.append("[layout]")
        if config.layout.sidebar_width is not None:
            lines.append(f"sidebar_width = {config.layout.sidebar_width}")
    if config.profiles:
        lines.append("")
        for profile in config.profiles:
            lines.append("[[profiles]]")
            lines.append(f'name = "{profile.name}"')
            if profile.dsn:
                lines.append(f'dsn = "{profile.dsn}"')
            if profile.host:
                lines.append(f'host = "{profile.host}"')
            if profile.port is not None:
                lines.append(f"port = {profile.port}")
            if profile.database:
                lines.append(f'database = "{profile.database}"')
            if profile.user:
                lines.append(f'user = "{profile.user}"')
            if profile.metadata_key:
                lines.append(f'metadata_key = "{profile.metadata_key}"')
            lines.append("")
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
        active_profile = raw.get("active_profile")
        if isinstance(active_profile, str):
            data["active_profile"] = active_profile
        profiles = raw.get("profiles")
        if isinstance(profiles, list):
            parsed_profiles: list[dict[str, object]] = []
            for profile in profiles:
                if not isinstance(profile, dict):
                    continue
                parsed: dict[str, object] = {}
                for key in ("name", "dsn", "host", "database", "user", "metadata_key"):
                    value = profile.get(key)
                    if isinstance(value, str):
                        parsed[key] = value
                port = profile.get("port")
                if isinstance(port, int):
                    parsed["port"] = port
                metadata = profile.get("metadata")
                if isinstance(metadata, dict):
                    tables: dict[str, tuple[str, ...]] = {}
                    for table, columns in metadata.items():
                        if isinstance(table, str) and isinstance(columns, list):
                            tables[table] = tuple(str(col) for col in columns)
                    parsed["metadata"] = tables
                if parsed.get("name"):
                    parsed_profiles.append(parsed)
            if parsed_profiles:
                data["profiles"] = parsed_profiles
        layout = raw.get("layout")
        if isinstance(layout, dict):
            state: dict[str, object] = {}
            sidebar_width = layout.get("sidebar_width")
            if isinstance(sidebar_width, int):
                state["sidebar_width"] = sidebar_width
            data["layout"] = LayoutState(**state)
    return data


def _default_profiles() -> tuple[ConnectionProfileConfig, ...]:
    """Default profiles shown on first run before config is customized."""

    return (
        ConnectionProfileConfig(
            name="Local Demo",
            host="localhost",
            port=5432,
            database="postgres",
            user="postgres",
            metadata_key="demo",
        ),
        ConnectionProfileConfig(
            name="Analytics Replica",
            host="localhost",
            port=5432,
            database="analytics",
            user="analytics",
            metadata_key="analytics",
        ),
    )
