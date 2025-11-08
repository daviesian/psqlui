"""Unit tests for the plugin command registry."""

from __future__ import annotations

import pytest

from psqlui.plugins import CommandCapability, PluginCommandRegistry


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _command(handler):
    return CommandCapability(name="hello", description="say hi", handler=handler)


def test_register_and_list_commands() -> None:
    registry = PluginCommandRegistry()
    registry.register(_command(lambda: None))

    commands = registry.list_commands()

    assert len(commands) == 1
    assert commands[0].name == "hello"


def test_register_raises_without_handler() -> None:
    registry = PluginCommandRegistry()

    with pytest.raises(ValueError):
        registry.register(CommandCapability(name="broken", description="no handler", handler=None))


@pytest.mark.anyio
async def test_execute_handles_sync_handler() -> None:
    executed: list[str] = []

    def _handler() -> None:
        executed.append("ok")

    registry = PluginCommandRegistry()
    registry.register(_command(_handler))

    await registry.execute("hello")

    assert executed == ["ok"]


@pytest.mark.anyio
async def test_execute_handles_async_handler() -> None:
    executed: list[str] = []

    async def _handler() -> None:
        executed.append("async")

    registry = PluginCommandRegistry()
    registry.register(_command(_handler))

    await registry.execute("hello")

    assert executed == ["async"]
