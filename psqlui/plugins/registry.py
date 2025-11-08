"""Registries and helpers for wiring plugin capabilities into the app."""

from __future__ import annotations

import inspect
from typing import Awaitable, Callable, Iterable

from .types import CommandCapability


class PluginCommandRegistry:
    """Collects command capabilities exposed by plugins."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandCapability] = {}

    def register(self, capability: CommandCapability) -> None:
        """Register a command capability."""

        if capability.handler is None:
            raise ValueError(f"Command '{capability.name}' is missing a handler")
        self._commands[capability.name] = capability

    def register_many(self, capabilities: Iterable[CommandCapability]) -> None:
        for capability in capabilities:
            self.register(capability)

    def list_commands(self) -> list[CommandCapability]:
        """Return the known commands."""

        return list(self._commands.values())

    async def execute(self, name: str, *args: object, **kwargs: object) -> None:
        """Execute a registered command by name."""

        capability = self._commands[name]
        handler = capability.handler
        assert handler is not None  # mypy appeasement; register() guards this
        result = handler(*args, **kwargs)
        if inspect.isawaitable(result):
            await result
        elif isinstance(result, Awaitable):
            await result
