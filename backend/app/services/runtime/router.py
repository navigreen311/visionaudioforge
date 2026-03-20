"""Model Router — selects optimal model based on latency, cost, and priority."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ModelRouteConfig:
    """Configuration for a registered model route."""

    model_id: str
    priority: int = 0
    max_latency_ms: int = 5000
    cost_per_inference: float = 0.0
    warm: bool = False
    fallback_model_id: str | None = None


class ModelRouter:
    """Route inference requests to the best-fit model based on constraints."""

    def __init__(self) -> None:
        self._models: dict[str, ModelRouteConfig] = {}
        self._fallback_chains: dict[str, list[str]] = {}
        self._executors: dict[str, Callable] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_model(self, model_id: str, config: ModelRouteConfig) -> None:
        """Register a model with its routing configuration."""
        config.model_id = model_id
        self._models[model_id] = config
        logger.info("Registered model %s (priority=%d, cost=%.4f)", model_id, config.priority, config.cost_per_inference)

    def register_executor(self, model_id: str, executor: Callable) -> None:
        """Register a callable that runs inference for a model."""
        self._executors[model_id] = executor

    # ------------------------------------------------------------------
    # Fallback chains
    # ------------------------------------------------------------------

    def add_fallback_chain(self, primary_id: str, fallback_ids: list[str]) -> None:
        """Define A -> B -> C fallback chain for a primary model."""
        self._fallback_chains[primary_id] = fallback_ids
        logger.info("Fallback chain for %s: %s", primary_id, " -> ".join(fallback_ids))

    def _get_fallback_chain(self, model_id: str) -> list[str]:
        """Return ordered list of fallback model IDs for *model_id*."""
        chain: list[str] = []
        if model_id in self._fallback_chains:
            chain.extend(self._fallback_chains[model_id])
        # Also check single-model fallback in config
        cfg = self._models.get(model_id)
        if cfg and cfg.fallback_model_id and cfg.fallback_model_id not in chain:
            chain.append(cfg.fallback_model_id)
        return chain

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(self, request_type: str, constraints: dict[str, Any] | None = None) -> dict[str, str]:
        """Select best model based on latency budget, cost, and priority.

        Parameters
        ----------
        request_type:
            Logical request category (unused in V1, reserved for future
            request-type-specific routing).
        constraints:
            Optional dict with ``max_latency_ms`` (int) to filter candidates.

        Returns
        -------
        dict with ``model_id`` and ``reason`` keys.
        """
        if not self._models:
            return {"model_id": "none", "reason": "no models registered"}

        constraints = constraints or {}
        max_latency = constraints.get("max_latency_ms")

        candidates = list(self._models.values())

        # Step 1: filter by latency budget
        if max_latency is not None:
            filtered = [m for m in candidates if m.max_latency_ms <= max_latency]
            if filtered:
                candidates = filtered

        # Step 2: sort by cost (ascending), then priority (descending)
        candidates.sort(key=lambda m: (m.cost_per_inference, -m.priority))

        best = candidates[0]
        reason_parts = [f"cheapest at ${best.cost_per_inference:.4f}"]
        if max_latency is not None:
            reason_parts.append(f"within {max_latency}ms latency budget")
        reason_parts.append(f"priority={best.priority}")

        return {"model_id": best.model_id, "reason": ", ".join(reason_parts)}

    # ------------------------------------------------------------------
    # Execution with fallback
    # ------------------------------------------------------------------

    async def execute_with_fallback(
        self, model_id: str, input_data: Any
    ) -> dict[str, Any]:
        """Try primary model, fall back through chain on failure."""
        chain = [model_id] + self._get_fallback_chain(model_id)

        for idx, mid in enumerate(chain):
            executor = self._executors.get(mid)
            if executor is None:
                logger.warning("No executor registered for model %s, skipping", mid)
                continue

            start = time.perf_counter()
            try:
                result = executor(input_data)
                elapsed_ms = (time.perf_counter() - start) * 1000
                return {
                    "result": result,
                    "model_used": mid,
                    "fallback_used": idx > 0,
                    "latency_ms": round(elapsed_ms, 2),
                }
            except Exception as exc:
                logger.warning("Model %s failed: %s — trying next fallback", mid, exc)
                continue

        return {
            "result": {"error": "all models in fallback chain failed"},
            "model_used": "none",
            "fallback_used": True,
            "latency_ms": 0.0,
        }
