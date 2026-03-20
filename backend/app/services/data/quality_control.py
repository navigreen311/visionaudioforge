"""Dataset quality control service — health checks, duplicates, corruption."""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections import defaultdict
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.services.data.storage import MinIOStorageService

logger = logging.getLogger(__name__)

BUCKET = "vaf-datasets"


class DatasetQualityService:
    """Analyse dataset quality: class balance, duplicates, corruption, etc."""

    # ------------------------------------------------------------------
    # Class imbalance
    # ------------------------------------------------------------------

    @staticmethod
    async def check_class_imbalance(
        db: AsyncSession,
        dataset_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Detect class imbalance.

        A dataset is considered *imbalanced* when the ratio of the largest
        class to the smallest class exceeds 5.
        """
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        class_counts: dict[str, int] = defaultdict(int)
        for a in assets:
            label = (a.metadata_ or {}).get("label")
            if label:
                class_counts[label] += 1

        if not class_counts:
            return {
                "is_imbalanced": False,
                "class_counts": {},
                "min_class": None,
                "max_class": None,
                "imbalance_ratio": 0.0,
                "recommendation": "No labeled samples found.",
            }

        counts = dict(class_counts)
        min_class = min(counts, key=counts.get)  # type: ignore[arg-type]
        max_class = max(counts, key=counts.get)  # type: ignore[arg-type]
        min_count = counts[min_class]
        max_count = counts[max_class]
        ratio = max_count / min_count if min_count > 0 else float("inf")
        is_imbalanced = ratio > 5

        if is_imbalanced:
            recommendation = (
                f"Class '{max_class}' has {max_count} samples vs '{min_class}' "
                f"with {min_count} (ratio {ratio:.1f}x). Consider: oversample "
                f"minority class, undersample majority class, or use class weights."
            )
        else:
            recommendation = "Class distribution is reasonably balanced."

        return {
            "is_imbalanced": is_imbalanced,
            "class_counts": counts,
            "min_class": min_class,
            "max_class": max_class,
            "imbalance_ratio": round(ratio, 2),
            "recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    # Health report
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_health_report(
        db: AsyncSession,
        dataset_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Generate a comprehensive dataset health report."""
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        total_samples = len(assets)
        if total_samples == 0:
            return {
                "total_samples": 0,
                "class_distribution": {},
                "is_imbalanced": False,
                "duplicate_count": 0,
                "corrupt_count": 0,
                "avg_size_bytes": 0.0,
                "modality_mix": {},
                "annotation_coverage": 0.0,
                "quality_score": 0.0,
                "issues": ["Dataset is empty."],
                "recommendations": ["Upload samples to the dataset."],
            }

        # Class distribution
        class_dist: dict[str, int] = defaultdict(int)
        modality_mix: dict[str, int] = defaultdict(int)
        annotated = 0
        total_size = 0
        duplicate_hashes: dict[str, int] = defaultdict(int)

        for a in assets:
            meta = a.metadata_ or {}
            label = meta.get("label")
            if label:
                class_dist[label] += 1
            if meta.get("annotations") or label:
                annotated += 1

            modality_mix[getattr(a, "media_type", "unknown")] += 1
            total_size += a.size_bytes or 0

            # Simple hash for duplicate detection (based on filename + size)
            h = hashlib.md5(f"{a.filename}:{a.size_bytes}".encode()).hexdigest()
            duplicate_hashes[h] += 1

        class_distribution = dict(class_dist)
        avg_size = total_size / total_samples if total_samples else 0.0
        annotation_coverage = annotated / total_samples if total_samples else 0.0
        duplicate_count = sum(v - 1 for v in duplicate_hashes.values() if v > 1)

        # Imbalance check
        is_imbalanced = False
        if class_distribution:
            counts = list(class_distribution.values())
            if min(counts) > 0:
                is_imbalanced = max(counts) / min(counts) > 5

        # Quality score (0-100)
        issues: list[str] = []
        recommendations: list[str] = []

        score = 100.0
        if is_imbalanced:
            score -= 20
            issues.append("Class distribution is imbalanced.")
            recommendations.append("Balance classes via oversampling or class weights.")
        if annotation_coverage < 0.5:
            score -= 20
            issues.append(f"Low annotation coverage: {annotation_coverage:.0%}.")
            recommendations.append("Label more samples or use auto-labeling.")
        if duplicate_count > 0:
            score -= min(15, duplicate_count * 3)
            issues.append(f"Found {duplicate_count} potential duplicate(s).")
            recommendations.append("Run deduplication to remove duplicates.")
        if total_samples < 50:
            score -= 15
            issues.append("Dataset has fewer than 50 samples.")
            recommendations.append("Collect more data or generate synthetic samples.")

        score = max(0.0, score)

        return {
            "total_samples": total_samples,
            "class_distribution": class_distribution,
            "is_imbalanced": is_imbalanced,
            "duplicate_count": duplicate_count,
            "corrupt_count": 0,  # Requires file loading; see detect_corrupt_samples
            "avg_size_bytes": round(avg_size, 2),
            "modality_mix": dict(modality_mix),
            "annotation_coverage": round(annotation_coverage, 4),
            "quality_score": round(score, 2),
            "issues": issues,
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------
    # Near-duplicate detection (perceptual hash)
    # ------------------------------------------------------------------

    @staticmethod
    async def find_near_duplicates(
        db: AsyncSession,
        storage: MinIOStorageService,
        dataset_id: uuid.UUID,
        threshold: float = 0.95,
    ) -> list[dict[str, Any]]:
        """Find near-duplicate image pairs using average (perceptual) hash.

        ``threshold`` is a similarity score (0–1); pairs above this value
        are considered near-duplicates.
        """
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        hashes: list[tuple[str, np.ndarray]] = []
        for asset in assets:
            try:
                data = await _try_load_bytes(asset, storage)
                if data is None:
                    continue
                h = _average_hash(data)
                if h is not None:
                    hashes.append((str(asset.id), h))
            except Exception as exc:
                logger.debug("Hash failed for %s: %s", asset.id, exc)

        # Compare all pairs
        duplicates: list[dict[str, Any]] = []
        hash_bits = 64  # 8x8 hash
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                hamming = int(np.sum(hashes[i][1] != hashes[j][1]))
                similarity = 1.0 - (hamming / hash_bits)
                if similarity >= threshold:
                    duplicates.append({
                        "pair": [hashes[i][0], hashes[j][0]],
                        "similarity": round(similarity, 4),
                    })

        duplicates.sort(key=lambda x: x["similarity"], reverse=True)
        return duplicates

    # ------------------------------------------------------------------
    # Corrupt sample detection
    # ------------------------------------------------------------------

    @staticmethod
    async def detect_corrupt_samples(
        db: AsyncSession,
        storage: MinIOStorageService,
        dataset_id: uuid.UUID,
    ) -> list[dict[str, str]]:
        """Try loading each asset file; if it fails, mark as corrupt."""
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        corrupt: list[dict[str, str]] = []
        for asset in assets:
            try:
                data = await _try_load_bytes(asset, storage)
                if data is None:
                    corrupt.append({
                        "asset_id": str(asset.id),
                        "error": "File not found or empty",
                    })
                    continue

                media = getattr(asset, "media_type", "") or ""
                if "image" in media:
                    import cv2

                    nparr = np.frombuffer(data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if img is None:
                        corrupt.append({
                            "asset_id": str(asset.id),
                            "error": "cv2.imread failed — corrupt or unsupported image",
                        })
                elif "audio" in media:
                    import io
                    import librosa  # type: ignore

                    librosa.load(io.BytesIO(data), sr=None)
            except Exception as exc:
                corrupt.append({
                    "asset_id": str(asset.id),
                    "error": str(exc),
                })

        return corrupt

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    async def deduplicate(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        keep: str = "first",
    ) -> dict[str, int]:
        """Remove exact duplicates (same filename + size). Keep 'first' or
        'last' occurrence.
        """
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        seen: dict[str, Asset] = {}
        to_remove: list[Asset] = []

        ordered = assets if keep == "first" else list(reversed(assets))

        for asset in ordered:
            key = f"{asset.filename}:{asset.size_bytes}"
            if key in seen:
                to_remove.append(asset)
            else:
                seen[key] = asset

        for asset in to_remove:
            meta = dict(asset.metadata_ or {})
            meta["removed_as_duplicate"] = True
            asset.metadata_ = meta

        await db.commit()
        return {"removed": len(to_remove), "kept": len(seen)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _try_load_bytes(
    asset: Asset, storage: MinIOStorageService | None = None
) -> bytes | None:
    """Try loading asset bytes from storage or local filesystem."""
    import os

    path = asset.storage_path if hasattr(asset, "storage_path") else None

    # Try local filesystem first
    if path and os.path.isfile(path):
        with open(path, "rb") as f:
            return f.read()

    # Try MinIO
    if storage and path and "/" in path:
        try:
            parts = path.split("/", 1)
            return await storage.download_file(parts[0], parts[1])
        except Exception:
            pass

    return None


def _average_hash(image_bytes: bytes, hash_size: int = 8) -> np.ndarray | None:
    """Compute an average perceptual hash for an image."""
    try:
        import cv2

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        resized = cv2.resize(img, (hash_size, hash_size))
        mean = resized.mean()
        return (resized > mean).flatten()
    except Exception:
        return None
