"""Auto-ML service: hyperparameter sweeps, backbone recommendation, and training recipes."""

import itertools
import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)

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
    ) -> list[dict[str, Any]]:
        """Run a grid search over *param_grid* up to *num_trials* configs.

        For each config the method simulates a training run and returns
        realistic (but synthetic) metrics so callers can evaluate the sweep
        without real GPU time.
        """
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        all_combos = list(itertools.product(*values))
        random.shuffle(all_combos)
        combos = all_combos[:num_trials]

        results: list[dict[str, Any]] = []
        for combo in combos:
            config = {**base_config, **dict(zip(keys, combo))}
            metrics = AutoMLService._simulate_training(config)
            results.append({"config": config, "metrics": metrics, "rank": 0})

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
            # Simulate validation metric variance for the preset
            variance = random.uniform(0.005, 0.05)
            if preset["name"] in ("light", "medium"):
                variance *= 0.5  # moderate augmentation tends to be most stable
            trials.append({"augmentation": preset, "val_metric_variance": round(variance, 5)})

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
        """Generate synthetic but realistic training metrics for a config."""
        lr = config.get("learning_rate", 0.001)
        epochs = config.get("epochs", config.get("num_epochs", 10))
        batch_size = config.get("batch_size", 32)

        # Base final loss influenced by hyper-params
        base_loss = 0.3 + abs(math.log10(lr + 1e-8)) * 0.05 + random.uniform(-0.05, 0.05)
        # Larger batch → slightly higher loss in small-data regime
        base_loss += (batch_size / 256) * 0.02

        train_loss = round(max(0.01, base_loss - 0.1 + random.gauss(0, 0.02)), 4)
        val_loss = round(max(0.01, base_loss + random.gauss(0, 0.03)), 4)
        accuracy = round(min(0.99, max(0.3, 1.0 - val_loss + random.gauss(0, 0.02))), 4)

        return {
            "train_loss": train_loss,
            "val_loss": val_loss,
            "accuracy": accuracy,
            "epochs_run": epochs,
        }
