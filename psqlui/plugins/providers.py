"""Command palette integrations for plugin capabilities."""

from __future__ import annotations

from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.types import IgnoreReturnCallbackType

from .registry import PluginCommandRegistry


class PluginCommandProvider(Provider):
    """Exposes plugin commands to Textual's command palette."""

    async def search(self, query: str) -> Hits:
        registry = self._registry
        if registry is None:
            return
        matcher = self.matcher(query)
        for capability in registry.list_commands():
            match = matcher.match(capability.name)
            if match > 0:
                yield Hit(
                    score=match,
                    match_display=matcher.highlight(capability.name),
                    command=self._build_callback(capability.name),
                    help=capability.description,
                )

    async def discover(self) -> Hits:
        registry = self._registry
        if registry is None:
            return
        for capability in registry.list_commands():
            yield DiscoveryHit(
                display=capability.name,
                command=self._build_callback(capability.name),
                help=capability.description,
            )

    @property
    def _registry(self) -> PluginCommandRegistry | None:
        registry = getattr(self.app, "command_registry", None)
        if isinstance(registry, PluginCommandRegistry):
            return registry
        return None

    def _build_callback(self, name: str) -> IgnoreReturnCallbackType:
        async def _run() -> None:
            registry = self._registry
            if registry is None:
                return
            await registry.execute(name)

        return _run
