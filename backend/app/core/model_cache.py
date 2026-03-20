"""Lazy model loading with automatic eviction of unused models."""

from __future__ import annotations

import sys
import threading
import time
from typing import Any, Callable


class ModelCache:
    """Singleton cache for ML models with LRU-style eviction.

    Models are loaded on first access and evicted when they haven't been
    used for ``max_age_seconds`` (default 300 s).
    """

    _instance: ModelCache | None = None
    _lock = threading.Lock()

    def __new__(cls) -> ModelCache:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._cache: dict[str, tuple[Any, float]] = {}
            return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_load(self, model_name: str, loader_fn: Callable[[], Any]) -> Any:
        """Return a cached model or load it via *loader_fn* on first use."""
        now = time.time()
        entry = self._cache.get(model_name)
        if entry is not None:
            model, _ = entry
            self._cache[model_name] = (model, now)
            return model

        model = loader_fn()
        self._cache[model_name] = (model, now)
        return model

    def evict_unused(self, max_age_seconds: float = 300) -> int:
        """Remove models not accessed within *max_age_seconds*. Returns count evicted."""
        now = time.time()
        to_evict = [
            name
            for name, (_, last_used) in self._cache.items()
            if (now - last_used) > max_age_seconds
        ]
        for name in to_evict:
            del self._cache[name]
        return len(to_evict)

    def get_stats(self) -> dict:
        """Return cache statistics."""
        cached_models = list(self._cache.keys())
        memory_estimate_mb = sum(
            sys.getsizeof(model) / (1024 * 1024)
            for model, _ in self._cache.values()
        )
        return {
            "cached_models": cached_models,
            "memory_estimate_mb": round(memory_estimate_mb, 2),
        }

    # ------------------------------------------------------------------
    # Testing helper
    # ------------------------------------------------------------------

    @classmethod
    def _reset(cls) -> None:
        """Reset the singleton (for tests only)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._cache.clear()
                cls._instance = None
