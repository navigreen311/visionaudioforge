"""Segmentation service: semantic and instance segmentation using OpenCV."""

from __future__ import annotations

import base64
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class SegmentationService:
    """Image segmentation using OpenCV GrabCut and threshold-based methods."""

    def semantic_segmentation(self, image: np.ndarray) -> dict:
        """Perform semantic segmentation (foreground/background).

        Uses GrabCut initialized with a rectangle covering the central
        region of the image to separate foreground from background.

        Returns:
            dict with mask (H,W int labels), classes list, and class_colors.
        """
        h, w = image.shape[:2]

        # Initialize mask for GrabCut
        mask = np.zeros((h, w), np.uint8)

        # Rectangle covering central 80% of image
        margin_x, margin_y = int(w * 0.1), int(h * 0.1)
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        try:
            cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        except cv2.error:
            logger.warning("GrabCut failed, falling back to threshold-based segmentation.")
            return self._threshold_segmentation(image)

        # Convert GrabCut mask to binary: 0=background, 1=foreground
        output_mask = np.where(
            (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0
        ).astype(np.uint8)

        classes = ["background", "foreground"]
        class_colors = {"background": [0, 0, 0], "foreground": [0, 255, 0]}

        return {
            "mask": output_mask,
            "classes": classes,
            "class_colors": class_colors,
        }

    def _threshold_segmentation(self, image: np.ndarray) -> dict:
        """Fallback threshold-based segmentation."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        _, binary = cv2.threshold(gray, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return {
            "mask": binary.astype(np.uint8),
            "classes": ["background", "foreground"],
            "class_colors": {"background": [0, 0, 0], "foreground": [0, 255, 0]},
        }

    def instance_segmentation(
        self, image: np.ndarray, detections: list[dict]
    ) -> list[dict]:
        """Instance segmentation using GrabCut within each detection bbox.

        Args:
            image: Input image (BGR).
            detections: List of dicts with at least 'bbox' [x1,y1,x2,y2] and 'class_name'.

        Returns:
            List of dicts with mask, class, bbox, and area for each instance.
        """
        instances = []
        h, w = image.shape[:2]

        for det in detections:
            bbox = det["bbox"]
            x1 = max(0, int(bbox[0]))
            y1 = max(0, int(bbox[1]))
            x2 = min(w, int(bbox[2]))
            y2 = min(h, int(bbox[3]))

            if x2 - x1 < 3 or y2 - y1 < 3:
                # Bbox too small for GrabCut
                instance_mask = np.zeros((h, w), dtype=np.uint8)
                instance_mask[y1:y2, x1:x2] = 1
            else:
                mask = np.zeros((h, w), np.uint8)
                rect = (x1, y1, x2 - x1, y2 - y1)
                bgd_model = np.zeros((1, 65), np.float64)
                fgd_model = np.zeros((1, 65), np.float64)

                try:
                    cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
                    instance_mask = np.where(
                        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0
                    ).astype(np.uint8)
                except cv2.error:
                    instance_mask = np.zeros((h, w), dtype=np.uint8)
                    instance_mask[y1:y2, x1:x2] = 1

            area = int(np.sum(instance_mask))

            instances.append({
                "mask": instance_mask,
                "class": det.get("class_name", "unknown"),
                "bbox": [x1, y1, x2, y2],
                "area": area,
            })

        return instances

    @staticmethod
    def mask_overlay(
        image: np.ndarray,
        masks: list[np.ndarray],
        colors: list[tuple[int, int, int]] | None = None,
        alpha: float = 0.5,
    ) -> np.ndarray:
        """Overlay colored masks on the image.

        Args:
            image: Input image (BGR, uint8).
            masks: List of binary masks (H, W).
            colors: Optional list of BGR color tuples per mask.
            alpha: Transparency for overlay (0=transparent, 1=opaque).

        Returns:
            Image with colored mask overlays.
        """
        overlay = image.copy()

        if colors is None:
            # Generate deterministic colors
            rng = np.random.default_rng(42)
            colors = [
                tuple(int(c) for c in rng.integers(50, 255, size=3))
                for _ in range(len(masks))
            ]

        for mask, color in zip(masks, colors):
            mask_bool = mask.astype(bool)
            if not np.any(mask_bool):
                continue
            colored = np.zeros_like(overlay)
            colored[:] = color
            overlay[mask_bool] = cv2.addWeighted(
                overlay[mask_bool].reshape(-1, 3),
                1 - alpha,
                colored[mask_bool].reshape(-1, 3),
                alpha,
                0,
            ).reshape(-1, 3)

        return overlay

    @staticmethod
    def export_masks(masks: list[np.ndarray], format: str = "png") -> list[str]:
        """Export masks as base64-encoded images.

        Args:
            masks: List of binary masks (H, W with values 0 or 1).
            format: Image format ('png' or 'jpg').

        Returns:
            List of base64-encoded image strings.
        """
        ext = f".{format}"
        encoded = []
        for mask in masks:
            # Scale binary mask to 0-255 for visibility
            visual = (mask * 255).astype(np.uint8)
            _, buf = cv2.imencode(ext, visual)
            b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
            encoded.append(b64)
        return encoded
