"""Batch processing utilities with concurrency control."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, Sequence, TypeVar

T = TypeVar("T")
R = TypeVar("R")


async def process_batch(
    items: Sequence[Any],
    processor_fn: Callable[[Any], Coroutine[Any, Any, Any]],
    batch_size: int = 10,
    max_concurrent: int = 5,
) -> list[Any]:
    """Process *items* in batches with bounded concurrency.

    Parameters
    ----------
    items:
        The full list of items to process.
    processor_fn:
        An async callable that processes a single item.
    batch_size:
        Number of items per batch.
    max_concurrent:
        Maximum number of items processed simultaneously within a batch
        (controlled via ``asyncio.Semaphore``).

    Returns
    -------
    list
        Results in the same order as *items*.
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[Any] = []

    async def _limited(item: Any) -> Any:
        async with semaphore:
            return await processor_fn(item)

    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        batch_results = await asyncio.gather(*[_limited(item) for item in batch])
        results.extend(batch_results)

    return results
