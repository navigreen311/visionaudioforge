"""Active learning service — intelligent sample selection for labeling."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset

logger = logging.getLogger(__name__)


class ActiveLearningService:
    """Select the most informative samples for human labeling."""

    # ------------------------------------------------------------------
    # Uncertainty sampling
    # ------------------------------------------------------------------

    @staticmethod
    async def uncertainty_sampling(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        model_name: str,
        k: int = 50,
    ) -> list[str]:
        """Select *k* unlabeled assets with the highest prediction entropy.

        Runs the model on each unlabeled asset, computes the entropy of the
        class-probability distribution, and returns the top-k most uncertain
        asset IDs.
        """
        assets = await _get_unlabeled_assets(db, dataset_id)
        if not assets:
            return []

        scored: list[tuple[str, float]] = []
        for asset in assets:
            try:
                probs = await _get_prediction_probs(asset, model_name)
                if probs is not None and len(probs) > 0:
                    entropy = _compute_entropy(probs)
                    scored.append((str(asset.id), entropy))
                else:
                    # If we can't get probs, assign moderate uncertainty
                    scored.append((str(asset.id), 0.5))
            except Exception as exc:
                logger.debug("Uncertainty scoring failed for %s: %s", asset.id, exc)
                scored.append((str(asset.id), 0.5))

        # Sort by entropy descending (most uncertain first)
        scored.sort(key=lambda x: x[1], reverse=True)
        return [asset_id for asset_id, _ in scored[:k]]

    # ------------------------------------------------------------------
    # Diversity sampling
    # ------------------------------------------------------------------

    @staticmethod
    async def diversity_sampling(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        k: int = 50,
    ) -> list[str]:
        """Select *k* diverse unlabeled assets via k-means clustering.

        Embeds all unlabeled assets into a feature space, clusters them into
        *k* groups, and selects the asset closest to each cluster centroid.
        """
        assets = await _get_unlabeled_assets(db, dataset_id)
        if not assets:
            return []

        # If fewer assets than k, return all
        if len(assets) <= k:
            return [str(a.id) for a in assets]

        # Build simple feature vectors from available metadata
        features = []
        valid_assets: list[Asset] = []
        for asset in assets:
            feat = _extract_simple_features(asset)
            features.append(feat)
            valid_assets.append(asset)

        if not features:
            return [str(a.id) for a in assets[:k]]

        feature_matrix = np.array(features, dtype=np.float32)

        # Normalize features
        norms = np.linalg.norm(feature_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        feature_matrix = feature_matrix / norms

        # Simple k-means clustering
        centroids, labels = _kmeans(feature_matrix, k, max_iter=20)

        # Select the asset closest to each centroid
        selected: list[str] = []
        for cluster_id in range(k):
            cluster_mask = labels == cluster_id
            if not np.any(cluster_mask):
                continue
            cluster_indices = np.where(cluster_mask)[0]
            cluster_features = feature_matrix[cluster_indices]
            distances = np.linalg.norm(
                cluster_features - centroids[cluster_id], axis=1
            )
            best_idx = cluster_indices[np.argmin(distances)]
            selected.append(str(valid_assets[best_idx].id))

        return selected

    # ------------------------------------------------------------------
    # Combined sampling
    # ------------------------------------------------------------------

    @staticmethod
    async def combined_sampling(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        model_name: str,
        k: int = 50,
        uncertainty_weight: float = 0.6,
    ) -> list[str]:
        """Combine uncertainty and diversity scores to select samples.

        ``score = uncertainty_weight * uncertainty + (1 - uncertainty_weight) * diversity``
        """
        assets = await _get_unlabeled_assets(db, dataset_id)
        if not assets:
            return []
        if len(assets) <= k:
            return [str(a.id) for a in assets]

        # Compute uncertainty scores
        uncertainty_scores: dict[str, float] = {}
        for asset in assets:
            try:
                probs = await _get_prediction_probs(asset, model_name)
                if probs is not None and len(probs) > 0:
                    uncertainty_scores[str(asset.id)] = _compute_entropy(probs)
                else:
                    uncertainty_scores[str(asset.id)] = 0.5
            except Exception:
                uncertainty_scores[str(asset.id)] = 0.5

        # Compute diversity scores (distance from nearest neighbor)
        features = [_extract_simple_features(a) for a in assets]
        feature_matrix = np.array(features, dtype=np.float32)
        norms = np.linalg.norm(feature_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        feature_matrix = feature_matrix / norms

        diversity_scores: dict[str, float] = {}
        for i, asset in enumerate(assets):
            dists = np.linalg.norm(feature_matrix - feature_matrix[i], axis=1)
            dists[i] = np.inf  # exclude self
            min_dist = float(np.min(dists))
            diversity_scores[str(asset.id)] = min_dist

        # Normalize both score sets to [0, 1]
        _normalize_scores(uncertainty_scores)
        _normalize_scores(diversity_scores)

        # Combine
        combined: list[tuple[str, float]] = []
        for asset in assets:
            aid = str(asset.id)
            score = (
                uncertainty_weight * uncertainty_scores.get(aid, 0.0)
                + (1 - uncertainty_weight) * diversity_scores.get(aid, 0.0)
            )
            combined.append((aid, score))

        combined.sort(key=lambda x: x[1], reverse=True)
        return [aid for aid, _ in combined[:k]]

    # ------------------------------------------------------------------
    # Review queue
    # ------------------------------------------------------------------

    @staticmethod
    async def create_review_queue(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        strategy: str = "combined",
        k: int = 50,
        model_name: str = "yolov8n",
    ) -> dict[str, Any]:
        """Create a prioritised review queue using the chosen strategy."""
        if strategy == "uncertainty":
            selected = await ActiveLearningService.uncertainty_sampling(
                db, dataset_id, model_name, k
            )
        elif strategy == "diversity":
            selected = await ActiveLearningService.diversity_sampling(
                db, dataset_id, k
            )
        else:
            selected = await ActiveLearningService.combined_sampling(
                db, dataset_id, model_name, k
            )

        queue_id = str(uuid.uuid4())
        items = [
            {"queue_item_id": str(uuid.uuid4()), "asset_id": aid}
            for aid in selected
        ]
        priority_scores = list(range(len(selected), 0, -1))

        return {
            "queue_id": queue_id,
            "items": items,
            "strategy": strategy,
            "priority_scores": priority_scores,
        }

    # ------------------------------------------------------------------
    # Process review decision
    # ------------------------------------------------------------------

    @staticmethod
    async def process_review(
        db: AsyncSession,
        queue_item_id: str,
        asset_id: uuid.UUID,
        decision: str,
        corrected_label: str | None = None,
    ) -> dict[str, Any]:
        """Process a human review decision for a queued item.

        ``decision`` is one of: 'approve', 'reject', 'correct'.
        """
        asset = await db.get(Asset, asset_id)
        if asset is None:
            return {"status": "error", "message": "Asset not found"}

        meta = dict(asset.metadata_ or {})
        annotations = meta.get("annotations", [])

        if decision == "approve":
            for ann in annotations:
                ann["is_verified"] = True
            meta["review_status"] = "approved"
        elif decision == "reject":
            meta["annotations"] = []
            meta.pop("label", None)
            meta["review_status"] = "rejected"
        elif decision == "correct" and corrected_label:
            meta["label"] = corrected_label
            meta["annotations"] = [{
                "label": corrected_label,
                "confidence": 1.0,
                "is_verified": True,
                "corrected_by_human": True,
            }]
            meta["review_status"] = "corrected"

        meta["reviewed_queue_item"] = queue_item_id
        asset.metadata_ = meta
        await db.commit()

        return {
            "status": "success",
            "decision": decision,
            "asset_id": str(asset_id),
            "label": meta.get("label"),
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_unlabeled_assets(
    db: AsyncSession, dataset_id: uuid.UUID
) -> list[Asset]:
    """Return assets in *dataset_id* that do not yet have a label."""
    result = await db.execute(
        select(Asset).where(
            Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
        )
    )
    assets = list(result.scalars().all())
    return [
        a for a in assets
        if not (a.metadata_ or {}).get("label")
        and not (a.metadata_ or {}).get("annotations")
    ]


async def _get_prediction_probs(
    asset: Asset, model_name: str
) -> np.ndarray | None:
    """Run inference and return class probabilities.

    Falls back to a random distribution when the model is unavailable so
    that the sampling logic can still function in test/dev environments.
    """
    try:
        from ultralytics import YOLO  # type: ignore

        model = YOLO(model_name)
        import cv2, os  # noqa: E401

        path = getattr(asset, "storage_path", None)
        if path and os.path.isfile(path):
            img = cv2.imread(path)
            if img is not None:
                results = model(img, verbose=False)
                if results[0].probs is not None:
                    return results[0].probs.data.cpu().numpy()
                # Detection model — use confidence scores as proxy
                confs = [float(b.conf[0]) for b in results[0].boxes]
                if confs:
                    arr = np.array(confs)
                    return arr / arr.sum()
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("Prediction failed for %s: %s", asset.id, exc)

    # Fallback: random probabilities for testing/dev
    rng = np.random.RandomState(hash(str(asset.id)) % (2**31))
    probs = rng.dirichlet(np.ones(10))
    return probs


def _extract_simple_features(asset: Asset) -> list[float]:
    """Create a lightweight feature vector from asset metadata."""
    meta = asset.metadata_ or {}
    size = float(asset.size_bytes or 0)
    # Use a hash of the filename as a pseudo-feature for diversity
    name_hash = hash(asset.filename) % 10000
    tag_count = len(getattr(asset, "tags", None) or [])
    return [size, float(name_hash), float(tag_count)]


def _compute_entropy(probs: np.ndarray) -> float:
    """Shannon entropy of a probability distribution."""
    probs = np.clip(probs, 1e-10, 1.0)
    probs = probs / probs.sum()
    return float(-np.sum(probs * np.log2(probs)))


def _normalize_scores(scores: dict[str, float]) -> None:
    """Normalize score values in-place to [0, 1]."""
    if not scores:
        return
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    rng = hi - lo if hi != lo else 1.0
    for k in scores:
        scores[k] = (scores[k] - lo) / rng


def _kmeans(
    data: np.ndarray, k: int, max_iter: int = 20
) -> tuple[np.ndarray, np.ndarray]:
    """Minimal k-means implementation (no sklearn dependency)."""
    n = data.shape[0]
    k = min(k, n)

    # Random initialisation
    rng = np.random.RandomState(42)
    indices = rng.choice(n, size=k, replace=False)
    centroids = data[indices].copy()

    labels = np.zeros(n, dtype=np.int32)
    for _ in range(max_iter):
        # Assign
        for i in range(n):
            dists = np.linalg.norm(centroids - data[i], axis=1)
            labels[i] = int(np.argmin(dists))
        # Update
        new_centroids = np.zeros_like(centroids)
        for c in range(k):
            members = data[labels == c]
            if len(members) > 0:
                new_centroids[c] = members.mean(axis=0)
            else:
                new_centroids[c] = centroids[c]
        if np.allclose(centroids, new_centroids):
            break
        centroids = new_centroids

    return centroids, labels
