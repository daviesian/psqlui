"""Async debounce helper used by the editor widgets."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


class Debouncer:
    """Utility that coalesces rapid-fire calls into a single coroutine run."""

    def __init__(self, delay: float = 0.15) -> None:
        self._delay = delay
        self._task: asyncio.Task[Any] | None = None

    def submit(self, coro_factory: Callable[[], Awaitable[Any]]) -> None:
        """Schedule a coroutine, cancelling any pending invocation."""

        if self._task:
            self._task.cancel()
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._runner(coro_factory))

    def cancel(self) -> None:
        """Cancel any pending invocation."""

        if self._task:
            self._task.cancel()
            self._task = None

    async def _runner(self, coro_factory: Callable[[], Awaitable[Any]]) -> None:
        try:
            await asyncio.sleep(self._delay)
            await coro_factory()
        except asyncio.CancelledError:
            return


__all__ = ["Debouncer"]
