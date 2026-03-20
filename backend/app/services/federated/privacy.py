"""Differential privacy for federated learning — Gaussian mechanism, gradient clipping."""

from __future__ import annotations

import math

import numpy as np


class DifferentialPrivacy:
    """Applies differential privacy guarantees to federated learning updates."""

    def add_noise(
        self,
        gradients: dict,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        clip_norm: float = 1.0,
    ) -> dict:
        """Gaussian mechanism: clip gradient norm, then add calibrated noise.

        Noise ~ N(0, sensitivity^2 * 2*ln(1.25/delta) / epsilon^2).
        """
        clipped = self.clip_gradients(gradients, max_norm=clip_norm)
        sensitivity = clip_norm
        sigma = sensitivity * math.sqrt(2.0 * math.log(1.25 / delta)) / epsilon

        noised: dict[str, np.ndarray] = {}
        for layer, params in clipped.items():
            arr = np.array(params, dtype=np.float64)
            noise = np.random.normal(0.0, sigma, size=arr.shape)
            noised[layer] = arr + noise

        return noised

    def clip_gradients(self, gradients: dict, max_norm: float) -> dict:
        """Per-sample gradient clipping to bound sensitivity."""
        clipped: dict[str, np.ndarray] = {}
        total_norm = 0.0
        for params in gradients.values():
            total_norm += float(np.linalg.norm(np.array(params, dtype=np.float64)) ** 2)
        total_norm = math.sqrt(total_norm)

        clip_factor = min(1.0, max_norm / max(total_norm, 1e-12))
        for layer, params in gradients.items():
            clipped[layer] = np.array(params, dtype=np.float64) * clip_factor

        return clipped

    def compute_privacy_budget(
        self,
        rounds: int,
        epsilon_per_round: float,
    ) -> dict:
        """Use advanced composition theorem to compute total privacy budget.

        Total epsilon ~ sqrt(2 * k * ln(1/delta)) * eps + k * eps * (e^eps - 1)
        Simplified to: sqrt(2k) * eps for small eps.
        """
        delta_per_round = 1e-5
        # Advanced composition
        total_epsilon = math.sqrt(2.0 * rounds * math.log(1.0 / delta_per_round)) * epsilon_per_round
        total_delta = rounds * delta_per_round

        if total_epsilon < 1.0:
            guarantee = "Strong privacy: individual contributions are well-protected"
        elif total_epsilon < 5.0:
            guarantee = "Moderate privacy: reasonable protection against inference"
        else:
            guarantee = "Weak privacy: limited protection, consider reducing rounds or epsilon"

        return {
            "total_epsilon": round(total_epsilon, 4),
            "total_delta": round(total_delta, 8),
            "privacy_guarantee": guarantee,
        }

    def is_budget_exhausted(self, spent_epsilon: float, total_budget: float) -> bool:
        """Check whether the privacy budget has been exhausted."""
        return spent_epsilon >= total_budget

    def privacy_report(
        self,
        federation_id: str,
        epsilon_spent: float = 0.0,
        epsilon_budget: float = 1.0,
        rounds_completed: int = 0,
        max_rounds: int = 50,
    ) -> dict:
        """Generate a privacy status report for the federation."""
        remaining_budget = max(0.0, epsilon_budget - epsilon_spent)
        if max_rounds > 0 and rounds_completed < max_rounds:
            eps_per_round = epsilon_budget / max_rounds
            rounds_remaining = int(remaining_budget / eps_per_round) if eps_per_round > 0 else 0
        else:
            rounds_remaining = 0

        ratio = epsilon_spent / max(epsilon_budget, 1e-12)
        if ratio < 0.3:
            privacy_level = "strong"
        elif ratio < 0.7:
            privacy_level = "moderate"
        else:
            privacy_level = "weak"

        return {
            "federation_id": federation_id,
            "epsilon_spent": round(epsilon_spent, 4),
            "epsilon_budget": epsilon_budget,
            "rounds_remaining": rounds_remaining,
            "privacy_level": privacy_level,
        }
