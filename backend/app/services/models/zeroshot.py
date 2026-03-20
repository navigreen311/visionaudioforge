"""Zero-shot classifier using CLIP-style text–image similarity."""

import logging
import math
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _softmax(scores: list[float]) -> list[float]:
    max_s = max(scores)
    exps = [math.exp(s - max_s) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class ZeroShotClassifier:
    """Zero-shot image classification via CLIP embeddings.

    If CLIP is not available the classifier falls back to uniform scores
    with a warning note.
    """

    def __init__(self) -> None:
        self._clip_available = False
        self._clip_model: Any = None
        self._clip_preprocess: Any = None
        self._tokenize: Any = None
        try:
            import clip  # type: ignore[import-untyped]
            import torch

            model, preprocess = clip.load("ViT-B/32", device="cpu")
            self._clip_model = model
            self._clip_preprocess = preprocess
            self._tokenize = clip.tokenize
            self._clip_available = True
            logger.info("CLIP loaded successfully for zero-shot classification.")
        except Exception:
            logger.warning("CLIP not available – zero-shot will return uniform scores.")

    # ------------------------------------------------------------------
    # Classify
    # ------------------------------------------------------------------

    def classify(
        self,
        image: np.ndarray,
        candidate_labels: list[str],
    ) -> dict[str, Any]:
        """Classify *image* against *candidate_labels* without any training examples."""
        if not candidate_labels:
            raise ValueError("candidate_labels must be a non-empty list.")

        if self._clip_available:
            return self._classify_clip(image, candidate_labels)

        # Fallback: uniform scores
        uniform = round(1.0 / len(candidate_labels), 4)
        all_scores = {label: uniform for label in candidate_labels}
        return {
            "predicted_label": candidate_labels[0],
            "confidence": uniform,
            "all_scores": all_scores,
            "note": "CLIP unavailable – scores are uniform.",
        }

    # ------------------------------------------------------------------
    # Compare zero-shot vs few-shot
    # ------------------------------------------------------------------

    def compare_with_fewshot(
        self,
        image: np.ndarray,
        zero_shot_labels: list[str],
        few_shot_centroids: dict[str, Any],
    ) -> dict[str, Any]:
        """Run both zero-shot and few-shot classification on the same image."""
        from app.services.models.fewshot import FewShotClassifier

        zs_result = self.classify(image, zero_shot_labels)
        fs_classifier = FewShotClassifier()
        fs_result = fs_classifier.predict(image, few_shot_centroids)

        agreement = zs_result.get("predicted_label") == fs_result.get("predicted_class")
        return {
            "zero_shot": zs_result,
            "few_shot": fs_result,
            "agreement": agreement,
        }

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _classify_clip(self, image: np.ndarray, labels: list[str]) -> dict[str, Any]:
        """Classify using the real CLIP model."""
        import torch
        from PIL import Image

        pil_img = Image.fromarray(image.astype(np.uint8))
        img_input = self._clip_preprocess(pil_img).unsqueeze(0)
        text_input = self._tokenize(labels)

        with torch.no_grad():
            img_feat = self._clip_model.encode_image(img_input)
            txt_feat = self._clip_model.encode_text(text_input)

        img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
        txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)

        sims = (img_feat @ txt_feat.T).squeeze(0).tolist()
        probs = _softmax(sims)
        all_scores = {label: round(p, 4) for label, p in zip(labels, probs)}

        best_idx = int(np.argmax(probs))
        return {
            "predicted_label": labels[best_idx],
            "confidence": round(probs[best_idx], 4),
            "all_scores": all_scores,
        }
