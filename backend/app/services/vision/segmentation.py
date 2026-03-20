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

    def panoptic_segmentation(
        self, image: np.ndarray, detections: list[dict] | None = None,
    ) -> dict:
        """Perform panoptic segmentation combining semantic and instance masks.

        Stuff regions are background areas not covered by any instance.
        Thing regions are individual instance masks with class labels.

        Args:
            image: Input image (BGR).
            detections: Optional list of dicts with 'bbox' and 'class_name'.

        Returns:
            dict with stuff_mask, thing_masks, combined_mask, and class_map.
        """
        h, w = image.shape[:2]

        # Semantic segmentation for background/foreground
        semantic = self.semantic_segmentation(image)
        semantic_mask = semantic["mask"]  # 0=background, 1=foreground

        # Instance segmentation for individual objects
        if detections:
            instances = self.instance_segmentation(image, detections)
        else:
            instances = []

        # Build combined mask with unique IDs
        # ID 0 = background stuff, ID 1+ = thing instances
        combined = np.zeros((h, w), dtype=np.int32)
        thing_masks: list[dict] = []
        class_map: dict[int, str] = {0: "background"}

        # Accumulate instance coverage
        instance_coverage = np.zeros((h, w), dtype=np.uint8)

        for idx, inst in enumerate(instances):
            instance_id = idx + 1
            inst_mask = inst["mask"].astype(np.uint8)
            combined[inst_mask > 0] = instance_id
            instance_coverage[inst_mask > 0] = 1
            class_name = inst.get("class", "unknown")
            class_map[instance_id] = class_name
            thing_masks.append({
                "instance_id": instance_id,
                "class": class_name,
                "mask": inst_mask,
                "bbox": inst.get("bbox", [0, 0, 0, 0]),
                "area": int(np.sum(inst_mask)),
            })

        # Stuff mask = foreground regions NOT covered by any instance
        stuff_mask = np.zeros((h, w), dtype=np.uint8)
        stuff_mask[(semantic_mask == 0) & (instance_coverage == 0)] = 1

        # Create colored combined visualization
        rng = np.random.default_rng(42)
        colored = np.zeros((h, w, 3), dtype=np.uint8)
        # Stuff regions in dark gray
        colored[stuff_mask > 0] = (50, 50, 50)
        # Each instance gets a unique color
        for thing in thing_masks:
            color = tuple(int(c) for c in rng.integers(80, 255, size=3))
            colored[thing["mask"] > 0] = color

        return {
            "stuff_mask": stuff_mask,
            "thing_masks": thing_masks,
            "combined_mask": colored,
            "class_map": class_map,
        }

    @staticmethod
    def mask_to_polygon(mask: np.ndarray) -> list[list[int]]:
        """Convert a binary mask to polygon contour points.

        Args:
            mask: Binary mask (H, W) with values 0 or 1.

        Returns:
            List of [x, y] coordinate pairs forming the polygon.
        """
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(
            mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
        )
        if not contours:
            return []

        # Return the largest contour
        largest = max(contours, key=cv2.contourArea)
        points = largest.reshape(-1, 2).tolist()
        return points

    @staticmethod
    def mask_iou(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
        """Compute intersection over union between two binary masks.

        Args:
            mask_a: Binary mask (H, W).
            mask_b: Binary mask (H, W).

        Returns:
            IoU score as float between 0.0 and 1.0.
        """
        a = mask_a.astype(bool)
        b = mask_b.astype(bool)
        intersection = np.logical_and(a, b).sum()
        union = np.logical_or(a, b).sum()
        if union == 0:
            return 0.0
        return float(intersection / union)

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
