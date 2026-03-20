"""License plate detection and blurring service."""

from __future__ import annotations

import cv2
import numpy as np


class PlateBlurService:
    """Detect and blur/redact license plates in images using contour analysis."""

    # Aspect-ratio bounds for license-plate-shaped rectangles
    _MIN_ASPECT = 2.0
    _MAX_ASPECT = 5.0
    _MIN_AREA = 800  # ignore tiny contours

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_plates(self, image: np.ndarray) -> list[dict]:
        """Detect license-plate-like rectangular regions.

        Returns a list of ``{"bbox": [x, y, w, h], "confidence": float}``.
        Confidence is a heuristic based on how close the aspect ratio is to
        the ideal ~3:1 plate shape.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()

        # Edge detection + morphological closing to link characters
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 100, 200)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        plates: list[dict] = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h == 0 or w * h < self._MIN_AREA:
                continue
            aspect = w / h
            if self._MIN_ASPECT <= aspect <= self._MAX_ASPECT:
                # Confidence: peaks at aspect ratio 3.0
                confidence = round(1.0 - min(abs(aspect - 3.0) / 2.0, 1.0), 2)
                plates.append({"bbox": [int(x), int(y), int(w), int(h)], "confidence": confidence})

        return plates

    # ------------------------------------------------------------------
    # Blur
    # ------------------------------------------------------------------

    def blur_plates(
        self, image: np.ndarray, plate_regions: list[dict] | None = None
    ) -> np.ndarray:
        """Apply heavy Gaussian blur (kernel 99) over each plate region."""
        if plate_regions is None:
            plate_regions = self.detect_plates(image)

        result = image.copy()
        for region in plate_regions:
            x, y, w, h = region["bbox"]
            roi = result[y : y + h, x : x + w]
            if roi.size == 0:
                continue
            blurred_roi = cv2.GaussianBlur(roi, (99, 99), 30)
            result[y : y + h, x : x + w] = blurred_roi
        return result

    # ------------------------------------------------------------------
    # Redact (solid fill)
    # ------------------------------------------------------------------

    def redact_plates(
        self,
        image: np.ndarray,
        plate_regions: list[dict] | None = None,
        fill_color: tuple = (0, 0, 0),
    ) -> np.ndarray:
        """Black-out (or fill) plate regions entirely."""
        if plate_regions is None:
            plate_regions = self.detect_plates(image)

        result = image.copy()
        for region in plate_regions:
            x, y, w, h = region["bbox"]
            result[y : y + h, x : x + w] = fill_color
        return result
