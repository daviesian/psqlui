"""Plugin loader implementation."""

from __future__ import annotations

import importlib.metadata as metadata
import inspect
import logging
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from psqlui import __version__ as CORE_VERSION

from .types import (
    CapabilitySpec,
    PluginCompatibilityError,
    PluginContext,
    PluginDescriptor,
    PluginError,
)

LOG = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "psqlui.plugins"


def _parse_version(value: str) -> tuple[int, int, int]:
    """Parse a dotted string into a comparable tuple."""

    parts = value.split(".")
    ints: list[int] = []
    for chunk in parts[:3]:
        try:
            ints.append(int(chunk))
        except ValueError:
            ints.append(0)
    while len(ints) < 3:
        ints.append(0)
    return ints[0], ints[1], ints[2]


@dataclass(slots=True, frozen=True)
class DiscoveredPlugin:
    """Metadata captured from entry point discovery."""

    name: str
    version: str
    min_core: str
    entry_point: metadata.EntryPoint
    descriptor: PluginDescriptor


@dataclass(slots=True, frozen=True)
class LoadedPlugin(DiscoveredPlugin):
    """Container for a registered plugin and its capabilities."""

    capabilities: Sequence[CapabilitySpec] = field(default_factory=tuple)


class PluginLoader:
    """Discovers and registers plugins exposed via entry points."""

    def __init__(
        self,
        ctx: PluginContext,
        *,
        core_version: str = CORE_VERSION,
        entry_point_group: str = ENTRY_POINT_GROUP,
        enabled_plugins: Iterable[str] | None = None,
        builtin_plugins: Iterable[PluginDescriptor | type[PluginDescriptor]] | None = None,
    ) -> None:
        self._ctx = ctx
        self._core_version = core_version
        self._entry_point_group = entry_point_group
        self._enabled: set[str] | None = set(enabled_plugins) if enabled_plugins is not None else None
        self._builtin_plugins = list(builtin_plugins or [])
        self._discovered: list[DiscoveredPlugin] = []
        self._loaded: dict[str, LoadedPlugin] = {}

    def discover(self) -> list[DiscoveredPlugin]:
        """Enumerate plugin descriptors from entry points."""

        eps = metadata.entry_points()
        group = eps.select(group=self._entry_point_group)
        discovered: dict[str, DiscoveredPlugin] = {}
        for entry_point in sorted(group, key=lambda ep: ep.name):
            descriptor = self._load_descriptor(entry_point)
            discovered[descriptor.name] = DiscoveredPlugin(
                name=descriptor.name,
                version=descriptor.version,
                min_core=getattr(descriptor, "min_core", "0.0.0"),
                entry_point=entry_point,
                descriptor=descriptor,
            )
        for builtin in self._iter_builtin_plugins():
            discovered.setdefault(builtin.name, builtin)
        self._discovered = list(discovered.values())
        return self._discovered

    def load(self) -> list[LoadedPlugin]:
        """Register capabilities for discovered plugins."""

        if not self._discovered:
            self.discover()

        loaded: list[LoadedPlugin] = []
        for plugin in self._discovered:
            if self._enabled is not None and plugin.name not in self._enabled:
                LOG.debug("Skipping disabled plugin", extra={"plugin": plugin.name})
                continue
            try:
                self._ensure_compatible(plugin)
            except PluginCompatibilityError as exc:
                LOG.warning(
                    "Skipping plugin due to min_core mismatch",
                    extra={"plugin": plugin.name, "min_core": plugin.min_core},
                )
                LOG.debug(str(exc))
                continue
            try:
                capabilities = tuple(plugin.descriptor.register(self._ctx))
            except Exception as exc:  # pragma: no cover - defensive logging path
                LOG.exception("Plugin registration failed", extra={"plugin": plugin.name})
                raise PluginError(f"Failed to register plugin '{plugin.name}'") from exc

            loaded_plugin = LoadedPlugin(
                name=plugin.name,
                version=plugin.version,
                min_core=plugin.min_core,
                entry_point=plugin.entry_point,
                descriptor=plugin.descriptor,
                capabilities=capabilities,
            )
            self._loaded[plugin.name] = loaded_plugin
            loaded.append(loaded_plugin)
        return loaded

    async def shutdown(self) -> None:
        """Invoke plugin shutdown hooks."""

        for plugin in self._loaded.values():
            try:
                await plugin.descriptor.on_shutdown()
            except Exception:  # pragma: no cover - defensive logging path
                LOG.exception("Plugin shutdown failed", extra={"plugin": plugin.name})

    @property
    def loaded(self) -> Sequence[LoadedPlugin]:
        """Return registered plugins."""

        return tuple(self._loaded.values())

    def _ensure_compatible(self, plugin: DiscoveredPlugin) -> None:
        core = _parse_version(self._core_version)
        minimum = _parse_version(plugin.min_core)
        if core < minimum:
            raise PluginCompatibilityError(
                f"Plugin '{plugin.name}' requires core>={plugin.min_core}, found {self._core_version}"
            )

    def _load_descriptor(self, entry_point: metadata.EntryPoint) -> PluginDescriptor:
        obj = entry_point.load()
        if inspect.isclass(obj):
            return obj()  # type: ignore[call-arg]
        return obj  # type: ignore[return-value]

    def _iter_builtin_plugins(self) -> list[DiscoveredPlugin]:
        builtins: list[DiscoveredPlugin] = []
        for plugin in self._builtin_plugins:
            descriptor = plugin() if inspect.isclass(plugin) else plugin
            entry_point = metadata.EntryPoint(
                name=descriptor.name,
                value=f"{descriptor.__class__.__module__}:{descriptor.__class__.__qualname__}",
                group=self._entry_point_group,
            )
            builtins.append(
                DiscoveredPlugin(
                    name=descriptor.name,
                    version=descriptor.version,
                    min_core=getattr(descriptor, "min_core", "0.0.0"),
                    entry_point=entry_point,
                    descriptor=descriptor,
                )
            )
        return builtins
