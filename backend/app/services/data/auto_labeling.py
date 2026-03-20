"""Auto-labeling service — model-assisted annotation for datasets."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset

logger = logging.getLogger(__name__)


class AutoLabelingService:
    """Automated and semi-automated labeling utilities for dataset assets."""

    # ------------------------------------------------------------------
    # Image auto-labeling
    # ------------------------------------------------------------------

    @staticmethod
    async def auto_label_images(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        model_name: str = "yolov8n",
        confidence_threshold: float = 0.7,
    ) -> dict[str, int]:
        """Run object detection on unlabeled images and create annotations.

        Returns counts of labeled, skipped (already labeled), and
        below-threshold detections.
        """
        from ultralytics import YOLO  # type: ignore

        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        model = YOLO(model_name)

        labeled = 0
        skipped = 0
        below_threshold = 0

        for asset in assets:
            meta = dict(asset.metadata_ or {})

            # Skip already-labeled assets
            if meta.get("label") or meta.get("annotations"):
                skipped += 1
                continue

            try:
                # Load image bytes and run inference
                import cv2

                img_bytes = await _load_asset_bytes(asset)
                if img_bytes is None:
                    skipped += 1
                    continue

                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    skipped += 1
                    continue

                results = model(img, verbose=False)
                detections = results[0]

                annotations = []
                has_valid = False
                for box in detections.boxes:
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    label = detections.names[cls_id]

                    if conf >= confidence_threshold:
                        annotations.append({
                            "label": label,
                            "confidence": round(conf, 4),
                            "bbox": box.xyxy[0].tolist(),
                            "is_verified": False,
                        })
                        has_valid = True
                    else:
                        below_threshold += 1

                if has_valid:
                    meta["annotations"] = annotations
                    meta["auto_labeled"] = True
                    meta["auto_label_model"] = model_name
                    asset.metadata_ = meta
                    labeled += 1
                elif not annotations:
                    skipped += 1

            except Exception as exc:
                logger.warning("Auto-label failed for asset %s: %s", asset.id, exc)
                skipped += 1

        await db.commit()
        return {"labeled": labeled, "skipped": skipped, "below_threshold": below_threshold}

    # ------------------------------------------------------------------
    # Audio auto-labeling
    # ------------------------------------------------------------------

    @staticmethod
    async def auto_label_audio(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        method: str = "classification",
    ) -> dict[str, int]:
        """Classify audio files and store labels as annotations.

        Uses a simple spectral-feature classifier approach.
        """
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        labeled = 0
        skipped = 0

        for asset in assets:
            meta = dict(asset.metadata_ or {})
            if meta.get("label") or meta.get("annotations"):
                skipped += 1
                continue

            try:
                audio_bytes = await _load_asset_bytes(asset)
                if audio_bytes is None:
                    skipped += 1
                    continue

                classification = _classify_audio(audio_bytes, method)
                if classification:
                    meta["label"] = classification["label"]
                    meta["annotations"] = [{
                        "label": classification["label"],
                        "confidence": classification["confidence"],
                        "is_verified": False,
                    }]
                    meta["auto_labeled"] = True
                    asset.metadata_ = meta
                    labeled += 1
                else:
                    skipped += 1
            except Exception as exc:
                logger.warning("Audio auto-label failed for %s: %s", asset.id, exc)
                skipped += 1

        await db.commit()
        return {"labeled": labeled, "skipped": skipped}

    # ------------------------------------------------------------------
    # Label suggestions
    # ------------------------------------------------------------------

    @staticmethod
    def suggest_labels(
        image: np.ndarray,
        model_name: str = "yolov8n",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Run inference and return top-k label suggestions with confidence."""
        from ultralytics import YOLO  # type: ignore

        model = YOLO(model_name)
        results = model(image, verbose=False)
        detections = results[0]

        suggestions: list[dict[str, Any]] = []
        for box in detections.boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = detections.names[cls_id]
            suggestions.append({"label": label, "confidence": round(conf, 4)})

        # Sort by confidence descending, return top_k
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions[:top_k]

    # ------------------------------------------------------------------
    # Label propagation (video sequences)
    # ------------------------------------------------------------------

    @staticmethod
    async def propagate_labels(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        source_frame_id: uuid.UUID,
        target_frame_ids: list[uuid.UUID],
    ) -> dict[str, int]:
        """Copy annotations from a source frame to target frames.

        Useful for video sequences where consecutive frames have similar
        content.
        """
        source = await db.get(Asset, source_frame_id)
        if source is None:
            return {"propagated": 0}

        source_meta = dict(source.metadata_ or {})
        source_annotations = source_meta.get("annotations", [])
        source_label = source_meta.get("label")

        if not source_annotations and not source_label:
            return {"propagated": 0}

        propagated = 0
        for target_id in target_frame_ids:
            target = await db.get(Asset, target_id)
            if target is None:
                continue

            meta = dict(target.metadata_ or {})
            if source_label:
                meta["label"] = source_label
            if source_annotations:
                meta["annotations"] = [
                    {**ann, "is_verified": False, "propagated_from": str(source_frame_id)}
                    for ann in source_annotations
                ]
            meta["propagated"] = True
            target.metadata_ = meta
            propagated += 1

        await db.commit()
        return {"propagated": propagated}

    # ------------------------------------------------------------------
    # Review queue (low-confidence auto-labels)
    # ------------------------------------------------------------------

    @staticmethod
    async def review_queue(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        confidence_range: tuple[float, float] = (0.3, 0.7),
    ) -> list[dict[str, Any]]:
        """Return assets whose auto-label confidence falls within the given
        range, indicating they need human review."""
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())
        low, high = confidence_range

        review_items: list[dict[str, Any]] = []
        for asset in assets:
            meta = asset.metadata_ or {}
            annotations = meta.get("annotations", [])
            for ann in annotations:
                conf = ann.get("confidence", 1.0)
                if low <= conf <= high and not ann.get("is_verified", True):
                    review_items.append({
                        "asset_id": str(asset.id),
                        "filename": asset.filename,
                        "annotation": ann,
                        "confidence": conf,
                    })
                    break  # one entry per asset

        review_items.sort(key=lambda x: x["confidence"])
        return review_items


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _load_asset_bytes(asset: Asset) -> bytes | None:
    """Attempt to read raw bytes for an asset from its storage path.

    In a production system this would go through MinIO; here we fall back to
    the local filesystem when the storage_path looks like a local path.
    """
    import os

    path = asset.storage_path
    if path and os.path.isfile(path):
        with open(path, "rb") as f:
            return f.read()
    return None


def _classify_audio(audio_bytes: bytes, method: str = "classification") -> dict | None:
    """Simple spectral-feature-based audio classification."""
    try:
        import io
        import librosa  # type: ignore

        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

        # Simple classification based on spectral centroid
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        rms = float(np.mean(librosa.feature.rms(y=y)))

        if rms < 0.01:
            label = "silence"
            confidence = 0.9
        elif centroid > 4000:
            label = "high_frequency"
            confidence = 0.75
        elif centroid > 2000:
            label = "mid_frequency"
            confidence = 0.7
        else:
            label = "low_frequency"
            confidence = 0.7

        return {"label": label, "confidence": round(confidence, 4)}
    except Exception as exc:
        logger.warning("Audio classification failed: %s", exc)
        return None
