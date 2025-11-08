"""Plugin contract primitives shared between loaders and extensions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, NamedTuple, Protocol, Sequence

from psqlui.config import AppConfig
from psqlui.sqlintel import SqlIntelService

PluginHandler = Callable[..., Awaitable[None] | None]


class CapabilityType(str, Enum):
    """Enumeration of supported plugin capability categories."""

    PANE = "pane"
    COMMAND = "command"
    EXPORTER = "exporter"
    METADATA_HOOK = "metadata_hook"
    SQL_ASSIST = "sql_assist"


class PluginContext(NamedTuple):
    """Runtime dependencies exposed to plugins."""

    app: Any | None = None
    event_bus: Any | None = None
    sql_intel: SqlIntelService | None = None
    metadata_cache: Any | None = None
    config: AppConfig | None = None


@dataclass(frozen=True, slots=True)
class PaneCapability:
    """Contribution describing a mountable widget or view."""

    name: str
    description: str
    region: str = "main"
    mount: Callable[[PluginContext], Any] | None = None


@dataclass(frozen=True, slots=True)
class CommandCapability:
    """Command palette or colon command contribution."""

    name: str
    description: str
    handler: PluginHandler | None = None


@dataclass(frozen=True, slots=True)
class ExporterCapability:
    """Result exporter contribution."""

    name: str
    formats: tuple[str, ...]
    handler: PluginHandler


@dataclass(frozen=True, slots=True)
class MetadataHookCapability:
    """Metadata enrichment hook."""

    name: str
    handler: PluginHandler


@dataclass(frozen=True, slots=True)
class SqlAssistCapability:
    """SQL assistance hook sitting on top of SqlIntelService."""

    name: str
    description: str
    handler: PluginHandler


CapabilitySpec = PaneCapability | CommandCapability | ExporterCapability | MetadataHookCapability | SqlAssistCapability


class PluginDescriptor(Protocol):
    """Contract implemented by third-party plugins."""

    name: str
    version: str
    min_core: str

    def register(self, ctx: PluginContext) -> Sequence[CapabilitySpec]: ...

    async def on_shutdown(self) -> None: ...


class PluginError(RuntimeError):
    """Base error for plugin loader failures."""


class PluginCompatibilityError(PluginError):
    """Raised when a plugin does not satisfy the minimum core version."""
