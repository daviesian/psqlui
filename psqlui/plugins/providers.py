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


class PluginToggleProvider(Provider):
    """Command palette provider for enabling/disabling plugins."""

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for hit in self._iter_hits():
            if (score := matcher.match(hit.text or "")) > 0:
                yield Hit(score, matcher.highlight(hit.text or ""), hit.command, help=hit.help)

    async def discover(self) -> Hits:
        for hit in self._iter_hits():
            yield hit

    def _iter_hits(self) -> list[DiscoveryHit]:
        app = self.app
        hits: list[DiscoveryHit] = []
        available = getattr(app, "available_plugins", lambda: ())()
        for plugin_name in available:
            enabled = getattr(app, "is_plugin_enabled", lambda *_: True)(plugin_name)
            if enabled:
                hits.append(
                    DiscoveryHit(
                        display=f"Disable plugin: {plugin_name}",
                        command=self._build_callback(plugin_name, False),
                        help="Persist disable in config (restart to take effect).",
                    )
                )
            else:
                hits.append(
                    DiscoveryHit(
                        display=f"Enable plugin: {plugin_name}",
                        command=self._build_callback(plugin_name, True),
                        help="Persist enable in config (restart to take effect).",
                    )
                )
        return hits

    def _build_callback(self, name: str, enabled: bool) -> IgnoreReturnCallbackType:
        async def _run() -> None:
            toggle = getattr(self.app, "toggle_plugin", None)
            if toggle is None:
                return
            toggle(name, enabled)

        return _run
