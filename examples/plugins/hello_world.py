"""Sample plugin implementing the contract for manual and automated tests."""

from __future__ import annotations

from typing import Sequence

from psqlui.plugins import (
    CapabilitySpec,
    CommandCapability,
    PaneCapability,
    PluginContext,
    PluginDescriptor,
)


class HelloWorldPlugin(PluginDescriptor):
    """Minimal descriptor used to validate the loader pipeline."""

    name = "hello-world"
    version = "0.0.1"
    min_core = "0.1.0"

    def __init__(self) -> None:
        self.shutdown_called = False
        self.registration_count = 0
        self.last_context: PluginContext | None = None
        self.executions = 0

    def register(self, ctx: PluginContext) -> Sequence[CapabilitySpec]:
        self.registration_count += 1
        self.last_context = ctx

        async def _handler(*_: object, **__: object) -> None:
            self.executions += 1

        return [
            CommandCapability(
                name="hello.world",
                description="Emit a friendly greeting toast.",
                handler=_handler,
            ),
            PaneCapability(
                name="Hello Pane",
                description="Static info panel contributed by hello-world plugin.",
                region="sidebar",
                mount=self._mount_pane,
            ),
        ]

    async def on_shutdown(self) -> None:
        self.shutdown_called = True

    def _mount_pane(self, ctx: PluginContext):  # type: ignore[override]
        from textual.widgets import Static

        return Static("Hello from plugin pane", id="hello-pane")
