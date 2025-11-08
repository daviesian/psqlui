"""Sample plugin implementing the contract for manual and automated tests."""

from __future__ import annotations

from typing import Sequence

from psqlui.plugins import (
    CapabilitySpec,
    CommandCapability,
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

    def register(self, ctx: PluginContext) -> Sequence[CapabilitySpec]:
        self.registration_count += 1
        self.last_context = ctx

        async def _handler(*_: object, **__: object) -> None:
            # Placeholder coroutine to satisfy the contract.
            return None

        return [
            CommandCapability(
                name="hello.world",
                description="Emit a friendly greeting toast.",
                handler=_handler,
            )
        ]

    async def on_shutdown(self) -> None:
        self.shutdown_called = True
