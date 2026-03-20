"""Few-shot classifier: build classifiers from handful of labelled examples."""

import logging
import math
from typing import Any, Callable

import numpy as np

logger = logging.getLogger(__name__)


def _default_embedding_fn(image: np.ndarray) -> np.ndarray:
    """Fallback embedding: flatten and truncate/pad to fixed 512-d vector."""
    flat = image.flatten().astype(np.float32)
    target_dim = 512
    if flat.shape[0] >= target_dim:
        vec = flat[:target_dim]
    else:
        vec = np.zeros(target_dim, dtype=np.float32)
        vec[: flat.shape[0]] = flat
    # L2-normalise
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class FewShotClassifier:
    """Nearest-centroid few-shot classifier using embeddings."""

    def __init__(self, embedding_fn: Callable[[np.ndarray], np.ndarray] | None = None):
        self._embed = embedding_fn or _default_embedding_fn

    # ------------------------------------------------------------------
    # Build class centroids from labelled examples
    # ------------------------------------------------------------------

    def build_classifier(
        self,
        examples: dict[str, list[np.ndarray]],
        embedding_fn: Callable[[np.ndarray], np.ndarray] | None = None,
    ) -> dict[str, Any]:
        """Compute centroid embeddings for each class.

        Parameters
        ----------
        examples : mapping of class-name → list of images (numpy arrays).
        embedding_fn : optional override for per-call embedding function.
        """
        embed = embedding_fn or self._embed
        class_centroids: dict[str, list[float]] = {}
        examples_per_class: dict[str, int] = {}

        for cls_name, images in examples.items():
            embeddings = [embed(img) for img in images]
            centroid = np.mean(embeddings, axis=0)
            # Re-normalise
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            class_centroids[cls_name] = centroid.tolist()
            examples_per_class[cls_name] = len(images)

        return {
            "class_centroids": class_centroids,
            "num_classes": len(class_centroids),
            "examples_per_class": examples_per_class,
        }

    # ------------------------------------------------------------------
    # Predict
    # ------------------------------------------------------------------

    def predict(
        self,
        image: np.ndarray,
        class_centroids: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify *image* by nearest centroid (cosine similarity)."""
        embedding = self._embed(image)
        scores: dict[str, float] = {}

        for cls_name, centroid in class_centroids.items():
            centroid_arr = np.array(centroid, dtype=np.float32)
            scores[cls_name] = round(_cosine_similarity(embedding, centroid_arr), 4)

        predicted = max(scores, key=scores.get)  # type: ignore[arg-type]
        return {
            "predicted_class": predicted,
            "confidence": scores[predicted],
            "all_scores": scores,
        }

    # ------------------------------------------------------------------
    # Evaluate
    # ------------------------------------------------------------------

    def evaluate(
        self,
        test_examples: dict[str, list[np.ndarray]],
        class_centroids: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate classifier against labelled test data."""
        class_names = sorted(class_centroids.keys())
        idx_map = {c: i for i, c in enumerate(class_names)}
        n = len(class_names)
        confusion = [[0] * n for _ in range(n)]

        correct = 0
        total = 0
        per_class: dict[str, dict[str, float]] = {}

        for true_cls, images in test_examples.items():
            cls_correct = 0
            for img in images:
                pred = self.predict(img, class_centroids)
                pred_cls = pred["predicted_class"]
                if true_cls in idx_map and pred_cls in idx_map:
                    confusion[idx_map[true_cls]][idx_map[pred_cls]] += 1
                if pred_cls == true_cls:
                    correct += 1
                    cls_correct += 1
                total += 1
            per_class[true_cls] = {
                "accuracy": round(cls_correct / max(len(images), 1), 4),
                "count": len(images),
            }

        return {
            "accuracy": round(correct / max(total, 1), 4),
            "per_class": per_class,
            "confusion_matrix": confusion,
        }

    # ------------------------------------------------------------------
    # Recommendation helper
    # ------------------------------------------------------------------

    @staticmethod
    def min_examples_recommendation(num_classes: int) -> dict[str, Any]:
        """Suggest minimum and recommended examples per class."""
        return {
            "minimum": 3,
            "recommended": max(5, num_classes * 2),
            "note": (
                f"For {num_classes} classes we recommend at least "
                f"{max(5, num_classes * 2)} examples per class for reliable few-shot results."
            ),
        }
