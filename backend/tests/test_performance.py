"""Performance-related unit tests: caching, model cache, batch, pool stats, query helpers."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Cache tests (mock Redis)
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_redis():
    """Return a mock redis.asyncio.Redis with an in-memory dict backend."""
    store: dict[str, str] = {}
    ttl_store: dict[str, float] = {}

    mock = AsyncMock()

    async def _get(key):
        # Check if expired
        if key in ttl_store and time.time() > ttl_store[key]:
            store.pop(key, None)
            ttl_store.pop(key, None)
            return None
        return store.get(key)

    async def _set(key, value, ex=None):
        store[key] = value
        if ex is not None:
            ttl_store[key] = time.time() + ex

    async def _delete(key):
        store.pop(key, None)
        ttl_store.pop(key, None)

    async def _scan_iter(match=None):
        import fnmatch

        for k in list(store.keys()):
            if match is None or fnmatch.fnmatch(k, match):
                yield k

    mock.get = AsyncMock(side_effect=_get)
    mock.set = AsyncMock(side_effect=_set)
    mock.delete = AsyncMock(side_effect=_delete)
    mock.scan_iter = _scan_iter
    mock.aclose = AsyncMock()

    # Expose store for assertions
    mock._store = store
    mock._ttl_store = ttl_store
    return mock


@pytest.fixture
def cache_service(fake_redis):
    from app.core.cache import CacheService

    svc = CacheService.__new__(CacheService)
    svc._redis = fake_redis
    return svc


@pytest.mark.anyio
async def test_cache_set_get_roundtrip(cache_service):
    """Values survive a set/get roundtrip with JSON serialization."""
    await cache_service.set("key1", {"hello": "world"}, ttl_seconds=60)
    result = await cache_service.get("key1")
    assert result == {"hello": "world"}


@pytest.mark.anyio
async def test_cache_ttl_expires(cache_service, fake_redis):
    """A key with a very short TTL should expire."""
    await cache_service.set("ephemeral", "data", ttl_seconds=1)
    # Manually expire by moving the ttl into the past
    fake_redis._ttl_store["ephemeral"] = time.time() - 1
    result = await cache_service.get("ephemeral")
    assert result is None


# ---------------------------------------------------------------------------
# Model cache tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_model_cache():
    from app.core.model_cache import ModelCache

    ModelCache._reset()
    yield
    ModelCache._reset()


def test_model_cache_reuses():
    """get_or_load should call loader_fn only once for the same model."""
    from app.core.model_cache import ModelCache

    mc = ModelCache()
    loader = MagicMock(return_value="my_model_object")

    result1 = mc.get_or_load("resnet50", loader)
    result2 = mc.get_or_load("resnet50", loader)

    assert result1 == "my_model_object"
    assert result2 == "my_model_object"
    loader.assert_called_once()


def test_model_cache_evict_unused():
    """evict_unused should remove models older than max_age_seconds."""
    from app.core.model_cache import ModelCache

    mc = ModelCache()
    mc.get_or_load("old_model", lambda: "old")
    # Backdate last_used
    model, _ = mc._cache["old_model"]
    mc._cache["old_model"] = (model, time.time() - 600)

    evicted = mc.evict_unused(max_age_seconds=300)
    assert evicted == 1
    assert "old_model" not in mc._cache


# ---------------------------------------------------------------------------
# Batch processing tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_batch_processing_respects_concurrency():
    """process_batch should not exceed max_concurrent simultaneous tasks."""
    from app.core.batch import process_batch

    peak = 0
    current = 0
    lock = asyncio.Lock()

    async def track(item):
        nonlocal peak, current
        async with lock:
            current += 1
            if current > peak:
                peak = current
        await asyncio.sleep(0.01)
        async with lock:
            current -= 1
        return item * 2

    items = list(range(20))
    results = await process_batch(items, track, batch_size=10, max_concurrent=3)

    assert results == [i * 2 for i in items]
    assert peak <= 3


# ---------------------------------------------------------------------------
# DB pool stats test
# ---------------------------------------------------------------------------


def test_db_pool_stats():
    """get_pool_stats should return the expected keys."""
    from app.database import get_pool_stats

    stats = get_pool_stats()
    assert "pool_size" in stats
    assert "checked_out" in stats
    assert "overflow" in stats


# ---------------------------------------------------------------------------
# Query helpers test
# ---------------------------------------------------------------------------


def test_pagination_helper():
    """paginate should chain .offset() and .limit() onto the query."""
    from app.core.query_helpers import paginate

    mock_query = MagicMock()
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query

    result = paginate(mock_query, skip=10, limit=25)
    mock_query.offset.assert_called_once_with(10)
    mock_query.limit.assert_called_once_with(25)
    assert result is mock_query
