"""Federated aggregation methods: FedAvg, FedProx, Trimmed Mean."""

from __future__ import annotations

import numpy as np


class FederatedAggregator:
    """Aggregation strategies for federated learning updates."""

    def fedavg(self, updates: list[dict], weights: list[float]) -> dict:
        """Weighted average of model parameters (Federated Averaging).

        Each update is ``{"layer_name": np.ndarray}``.
        Result = sum(w_i * update_i) / sum(w_i).
        """
        if not updates:
            raise ValueError("No updates to aggregate")

        total_weight = sum(weights)
        if total_weight == 0:
            raise ValueError("Total weight is zero")

        normalised = [w / total_weight for w in weights]
        layer_names = updates[0].keys()
        result: dict[str, np.ndarray] = {}

        for layer in layer_names:
            weighted_sum = sum(
                n * np.array(u[layer], dtype=np.float64)
                for n, u in zip(normalised, updates)
                if layer in u
            )
            result[layer] = weighted_sum

        return result

    def fedprox(
        self,
        updates: list[dict],
        weights: list[float],
        global_model: dict,
        mu: float = 0.01,
    ) -> dict:
        """FedAvg + proximal term penalty for drift from global model."""
        avg = self.fedavg(updates, weights)
        result: dict[str, np.ndarray] = {}

        for layer, params in avg.items():
            if layer in global_model:
                global_params = np.array(global_model[layer], dtype=np.float64)
                # Apply proximal correction: move result closer to global
                result[layer] = params - mu * (params - global_params)
            else:
                result[layer] = params

        return result

    def trimmed_mean(
        self,
        updates: list[dict],
        weights: list[float],
        trim_ratio: float = 0.1,
    ) -> dict:
        """Remove top/bottom trim_ratio of values per parameter before averaging.

        Robust to outliers and Byzantine participants.
        """
        if not updates:
            raise ValueError("No updates to aggregate")

        n = len(updates)
        trim_count = max(1, int(n * trim_ratio)) if n > 2 else 0
        layer_names = updates[0].keys()
        result: dict[str, np.ndarray] = {}

        for layer in layer_names:
            stacked = np.stack(
                [np.array(u[layer], dtype=np.float64) for u in updates if layer in u]
            )
            if trim_count > 0 and stacked.shape[0] > 2 * trim_count:
                sorted_stack = np.sort(stacked, axis=0)
                trimmed = sorted_stack[trim_count : -trim_count]
            else:
                trimmed = stacked
            result[layer] = np.mean(trimmed, axis=0)

        return result

    def validate_update(self, update: dict, global_model: dict) -> dict:
        """Validate that an update is compatible with the global model."""
        issues: list[str] = []

        for layer, params in update.items():
            arr = np.array(params, dtype=np.float64)

            # Check for NaN / Inf
            if np.any(np.isnan(arr)):
                issues.append(f"Layer '{layer}' contains NaN values")
            if np.any(np.isinf(arr)):
                issues.append(f"Layer '{layer}' contains Inf values")

            # Check dimension match
            if layer in global_model:
                global_arr = np.array(global_model[layer])
                if arr.shape != global_arr.shape:
                    issues.append(
                        f"Layer '{layer}' shape {arr.shape} != global {global_arr.shape}"
                    )

                # Check magnitude (>100x global)
                global_norm = np.linalg.norm(global_arr)
                if global_norm > 0:
                    update_norm = np.linalg.norm(arr)
                    if update_norm > 100 * global_norm:
                        issues.append(
                            f"Layer '{layer}' magnitude {update_norm:.1f} exceeds "
                            f"100x global magnitude {global_norm:.1f}"
                        )

        return {"valid": len(issues) == 0, "issues": issues}
