"""Redis caching service with decorator support."""

from __future__ import annotations

import functools
import hashlib
import json
from typing import Any, Callable

import redis.asyncio as redis


class CacheService:
    """Async Redis cache with JSON serialization."""

    def __init__(self, redis_url: str) -> None:
        self._redis: redis.Redis = redis.from_url(
            redis_url, decode_responses=True
        )

    async def get(self, key: str) -> Any | None:
        """Get a value from cache, JSON-deserialized."""
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(
        self, key: str, value: Any, ttl_seconds: int = 300
    ) -> None:
        """Set a value in cache, JSON-serialized with TTL."""
        await self._redis.set(key, json.dumps(value), ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        """Delete a single key from cache."""
        await self._redis.delete(key)

    async def clear_prefix(self, prefix: str) -> int:
        """Delete all keys matching a prefix. Returns count deleted."""
        count = 0
        async for key in self._redis.scan_iter(match=f"{prefix}*"):
            await self._redis.delete(key)
            count += 1
        return count

    @staticmethod
    def cache_key(module: str, operation: str, *args: Any) -> str:
        """Build a deterministic cache key."""
        args_hash = hashlib.sha256(
            json.dumps(args, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        return f"vaf:{module}:{operation}:{args_hash}"

    async def close(self) -> None:
        """Close the underlying Redis connection."""
        await self._redis.aclose()


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------
_cache_service: CacheService | None = None


def get_cache_service(redis_url: str | None = None) -> CacheService:
    """Return (or create) the module-level CacheService singleton."""
    global _cache_service
    if _cache_service is None:
        if redis_url is None:
            from app.config import settings
            redis_url = settings.REDIS_URL
        _cache_service = CacheService(redis_url)
    return _cache_service


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------
def cached(ttl: int = 300, prefix: str = "general"):
    """Decorator that caches an async function's return value in Redis.

    Usage::

        @cached(ttl=120, prefix="vision")
        async def heavy_computation(x, y):
            ...
    """

    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any):
            svc = get_cache_service()
            key = CacheService.cache_key(
                prefix, fn.__name__, *args, *sorted(kwargs.items())
            )
            hit = await svc.get(key)
            if hit is not None:
                return hit
            result = await fn(*args, **kwargs)
            await svc.set(key, result, ttl_seconds=ttl)
            return result

        return wrapper

    return decorator
