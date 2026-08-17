"""Auto-ML service: hyperparameter sweeps, backbone recommendation, and training recipes."""

import hashlib
import itertools
import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)

#: Default seed for the sampling that random search legitimately needs. Fixed so
#: a sweep is reproducible; callers can override per call.
DEFAULT_SWEEP_SEED = 0


def _unit_hash(*parts: str) -> float:
    """Stable pseudo-value in [0, 1) derived from *parts*.

    Used to make simulated training metrics deterministic. random.* here meant
    the same hyper-parameter config scored differently on every sweep, which
    makes a "best config" recommendation meaningless.
    """
    digest = hashlib.sha256("|".join(parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)

# ---------------------------------------------------------------------------
# Training recipe presets
# ---------------------------------------------------------------------------

TRAINING_RECIPES: dict[str, dict[str, Any]] = {
    "image_classification": {
        "backbone": "resnet50",
        "learning_rate": 0.001,
        "epochs": 20,
        "batch_size": 32,
        "augmentation": "light",
    },
    "audio_classification": {
        "backbone": "resnet18",
        "learning_rate": 0.001,
        "epochs": 30,
        "batch_size": 64,
        "n_mfcc": 13,
    },
    "object_detection": {
        "backbone": "yolov8n",
        "learning_rate": 0.01,
        "epochs": 50,
        "batch_size": 16,
    },
    "fine_grained": {
        "backbone": "clip",
        "learning_rate": 0.0001,
        "epochs": 10,
        "batch_size": 16,
        "freeze": True,
    },
    "quick_prototype": {
        "backbone": "resnet18",
        "learning_rate": 0.01,
        "epochs": 5,
        "batch_size": 64,
    },
}


class AutoMLService:
    """Automated machine-learning helpers for hyperparameter search and configuration."""

    # ------------------------------------------------------------------
    # Hyperparameter sweep (V1 – grid search with simulated metrics)
    # ------------------------------------------------------------------

    @staticmethod
    def hyperparameter_sweep(
        base_config: dict[str, Any],
        param_grid: dict[str, list[Any]],
        num_trials: int = 10,
        seed: int = DEFAULT_SWEEP_SEED,
    ) -> list[dict[str, Any]]:
        """Run a randomised search over *param_grid* up to *num_trials* configs.

        No training is performed. Each trial's metrics come from
        ``_simulate_training`` and every result carries ``simulated: True`` —
        the ranking shows how the sweep *would* be ordered, not measured
        outcomes.
        """
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        all_combos = list(itertools.product(*values))
        # Randomised order is the actual search strategy here, so it stays —
        # but seeded, so a sweep can be reproduced and compared.
        random.Random(seed).shuffle(all_combos)
        combos = all_combos[:num_trials]

        results: list[dict[str, Any]] = []
        for combo in combos:
            config = {**base_config, **dict(zip(keys, combo))}
            metrics = AutoMLService._simulate_training(config)
            results.append(
                {"config": config, "metrics": metrics, "rank": 0, "simulated": True}
            )

        # Rank by val_loss ascending (lower is better)
        results.sort(key=lambda r: r["metrics"]["val_loss"])
        for idx, r in enumerate(results):
            r["rank"] = idx + 1

        return results

    # ------------------------------------------------------------------
    # Backbone recommender
    # ------------------------------------------------------------------

    @staticmethod
    def recommend_backbone(dataset_stats: dict[str, Any]) -> dict[str, Any]:
        """Recommend a pretrained backbone based on dataset statistics."""
        samples = dataset_stats.get("num_samples", 0)
        modality = dataset_stats.get("modality", "image")

        if modality == "audio":
            return {
                "recommended": "resnet18",
                "reason": "ResNet-18 on spectrograms is efficient for audio tasks.",
                "alternatives": ["resnet50"],
            }
        if modality == "multimodal":
            return {
                "recommended": "clip",
                "reason": "CLIP handles multimodal image+text natively.",
                "alternatives": ["clip-vit"],
            }
        if samples < 1000:
            return {
                "recommended": "resnet18",
                "reason": "Small dataset (<1 000 samples); a lightweight backbone avoids overfitting.",
                "alternatives": ["mobilenetv3"],
            }
        if samples < 10000:
            return {
                "recommended": "resnet50",
                "reason": "Medium dataset benefits from deeper capacity without being excessive.",
                "alternatives": ["resnet18", "efficientnet_b0"],
            }
        return {
            "recommended": "clip-vit",
            "reason": "Large dataset (>10 000 samples) can leverage a heavy vision-transformer backbone.",
            "alternatives": ["resnet50", "vit_base"],
        }

    # ------------------------------------------------------------------
    # Auto augmentation search (V1 – preset evaluation)
    # ------------------------------------------------------------------

    @staticmethod
    def auto_augmentation_search(
        dataset_id: str,
        num_trials: int = 5,
    ) -> dict[str, Any]:
        """Try augmentation presets and pick the one with lowest metric variance."""
        presets = [
            {"name": "none", "flip": False, "rotate": 0, "color_jitter": 0.0},
            {"name": "light", "flip": True, "rotate": 15, "color_jitter": 0.1},
            {"name": "medium", "flip": True, "rotate": 30, "color_jitter": 0.2},
            {"name": "heavy", "flip": True, "rotate": 45, "color_jitter": 0.4},
            {"name": "aggressive", "flip": True, "rotate": 90, "color_jitter": 0.5},
        ]

        trials: list[dict[str, Any]] = []
        for preset in presets[:num_trials]:
            # Modelled, not measured: no training runs to observe variance from.
            # Deterministic per preset so the recommendation is stable — with
            # random.uniform the "best" augmentation changed on every call.
            variance = 0.005 + _unit_hash(str(preset["name"]), "variance") * 0.045
            if preset["name"] in ("light", "medium"):
                variance *= 0.5  # moderate augmentation tends to be most stable
            trials.append(
                {
                    "augmentation": preset,
                    "val_metric_variance": round(variance, 5),
                    "simulated": True,
                }
            )

        trials.sort(key=lambda t: t["val_metric_variance"])
        return {
            "best_config": trials[0]["augmentation"],
            "all_trials": trials,
        }

    # ------------------------------------------------------------------
    # Training recipes
    # ------------------------------------------------------------------

    @staticmethod
    def training_recipe(use_case: str) -> dict[str, Any]:
        """Return a preset training configuration for a known use-case."""
        recipe = TRAINING_RECIPES.get(use_case)
        if recipe is None:
            available = list(TRAINING_RECIPES.keys())
            raise ValueError(f"Unknown use_case '{use_case}'. Available: {available}")
        return {**recipe, "use_case": use_case}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _simulate_training(config: dict[str, Any]) -> dict[str, Any]:
        """Model synthetic training metrics for a config.

        These are NOT measurements — no training runs. The values are a
        deterministic function of the config so the same hyper-parameters always
        score the same, making a sweep's ranking reproducible. Callers must
        surface the accompanying ``simulated`` flag.
        """
        lr = config.get("learning_rate", 0.001)
        epochs = config.get("epochs", config.get("num_epochs", 10))
        batch_size = config.get("batch_size", 32)
        key = f"lr={lr},epochs={epochs},bs={batch_size}"

        # Base final loss influenced by hyper-params, plus a deterministic
        # per-config offset standing in for run-to-run variance.
        base_loss = 0.3 + abs(math.log10(lr + 1e-8)) * 0.05
        base_loss += (_unit_hash(key, "base") - 0.5) * 0.10
        # Larger batch → slightly higher loss in small-data regime
        base_loss += (batch_size / 256) * 0.02

        train_loss = round(
            max(0.01, base_loss - 0.1 + (_unit_hash(key, "train") - 0.5) * 0.04), 4
        )
        val_loss = round(
            max(0.01, base_loss + (_unit_hash(key, "val") - 0.5) * 0.06), 4
        )
        accuracy = round(
            min(0.99, max(0.3, 1.0 - val_loss + (_unit_hash(key, "acc") - 0.5) * 0.04)),
            4,
        )

        return {
            "train_loss": train_loss,
            "val_loss": val_loss,
            "accuracy": accuracy,
            "epochs_run": epochs,
        }
