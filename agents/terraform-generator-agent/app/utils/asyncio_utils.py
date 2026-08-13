from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar


T = TypeVar("T")


def run_awaitable(awaitable: Awaitable[T]) -> T:
    """
    Run an awaitable from synchronous code in both main-thread and worker-thread
    contexts.

    FastAPI calls the generator inside a threadpool, where get_event_loop() may
    raise RuntimeError because no event loop is set for that thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("run_awaitable() cannot be used from an active event loop thread.")
