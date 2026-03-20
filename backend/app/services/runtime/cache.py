"""Inference Cache — Redis-backed cache for inference results."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class InferenceCache:
    """Cache inference results in Redis with TTL-based expiration."""

    def __init__(self, redis_url: str = "", ttl_seconds: int = 3600) -> None:
        self._redis_url = redis_url
        self._ttl = ttl_seconds
        self._redis: Any | None = None

        # In-memory fallback when Redis is unavailable
        self._mem_cache: dict[str, str] = {}
        self._hit_count: int = 0
        self._miss_count: int = 0

        self._try_connect()

    def _try_connect(self) -> None:
        """Attempt to connect to Redis; fall back to in-memory cache."""
        if not self._redis_url:
            logger.info("No Redis URL provided — using in-memory inference cache")
            return
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            logger.info("Connected to Redis for inference caching")
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — using in-memory cache", exc)
            self._redis = None

    # ------------------------------------------------------------------
    # Key computation
    # ------------------------------------------------------------------

    @staticmethod
    def cache_key(model_id: str, input_hash: str) -> str:
        """Build a namespaced cache key."""
        return f"infer:{model_id}:{input_hash}"

    @staticmethod
    def _hash_input(input_data: Any) -> str:
        """Compute SHA-256 hex digest of serialized input."""
        serialized = json.dumps(input_data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Get / Set / Invalidate
    # ------------------------------------------------------------------

    async def get(self, model_id: str, input_data: Any) -> dict | None:
        """Return cached result or ``None`` on miss."""
        h = self._hash_input(input_data)
        key = self.cache_key(model_id, h)

        if self._redis is not None:
            try:
                raw = await self._redis.get(key)
                if raw is not None:
                    self._hit_count += 1
                    return json.loads(raw)
                self._miss_count += 1
                return None
            except Exception:
                pass

        # Fallback to in-memory
        if key in self._mem_cache:
            self._hit_count += 1
            return json.loads(self._mem_cache[key])
        self._miss_count += 1
        return None

    async def set(
        self,
        model_id: str,
        input_data: Any,
        result: dict,
        ttl: int | None = None,
    ) -> None:
        """Store inference result in cache."""
        h = self._hash_input(input_data)
        key = self.cache_key(model_id, h)
        value = json.dumps(result, default=str)
        ttl = ttl or self._ttl

        if self._redis is not None:
            try:
                await self._redis.set(key, value, ex=ttl)
                return
            except Exception:
                pass

        # Fallback to in-memory
        self._mem_cache[key] = value

    async def invalidate(self, model_id: str | None = None) -> int:
        """Clear cache entries. If *model_id* given, clear only that model."""
        count = 0

        if self._redis is not None:
            try:
                pattern = f"infer:{model_id}:*" if model_id else "infer:*"
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        count += len(keys)
                        await self._redis.delete(*keys)
                    if cursor == 0:
                        break
                return count
            except Exception:
                pass

        # Fallback to in-memory
        prefix = f"infer:{model_id}:" if model_id else "infer:"
        keys_to_delete = [k for k in self._mem_cache if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._mem_cache[k]
        count = len(keys_to_delete)
        return count

    async def get_cache_stats(self) -> dict[str, Any]:
        """Return cache hit/miss statistics."""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0.0

        # Count entries
        entries = 0
        size_bytes = 0

        if self._redis is not None:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match="infer:*", count=100)
                    entries += len(keys)
                    if cursor == 0:
                        break
            except Exception:
                entries = len(self._mem_cache)
                size_bytes = sum(len(v) for v in self._mem_cache.values())
        else:
            entries = len(self._mem_cache)
            size_bytes = sum(len(v) for v in self._mem_cache.values())

        return {
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": round(hit_rate, 4),
            "size_mb": round(size_bytes / (1024 * 1024), 4),
            "entries": entries,
        }
