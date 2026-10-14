"""Bounded blocking work: cancellation drains the thread before releasing its slot."""

import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


async def run_blocking(function: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    work = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(work)
    except asyncio.CancelledError:
        # Threads cannot be killed safely. Discard their output, but do not allow
        # repeated cancellation to create unbounded orphaned parser/render threads.
        with suppress(Exception):
            await work
        raise
