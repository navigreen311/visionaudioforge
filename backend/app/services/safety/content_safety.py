"""ContentSafetyChecker — image safety heuristics, deepfake risk, watermarking."""

from __future__ import annotations

import cv2
import numpy as np


class ContentSafetyChecker:
    """Lightweight content-safety checks for images."""

    async def check_image_safety(self, image: np.ndarray) -> dict:
        """Check basic image-quality safety flags.

        Flags raised for:
        - Image too small (< 10x10)
        - Image too dark or too bright (> 90 % pixels at extremes)
        - Solid-color / very-low-variance image
        """
        flags: list[str] = []
        h, w = image.shape[:2]

        if h < 10 or w < 10:
            flags.append("image_too_small")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image

        total_pixels = gray.size
        dark_ratio = np.sum(gray < 15) / total_pixels
        bright_ratio = np.sum(gray > 240) / total_pixels

        if dark_ratio > 0.9:
            flags.append("image_too_dark")
        if bright_ratio > 0.9:
            flags.append("image_too_bright")

        if np.std(gray) < 2.0:
            flags.append("solid_color_image")

        return {"safe": len(flags) == 0, "flags": flags}

    async def check_deepfake_risk(self, image: np.ndarray) -> dict:
        """Estimate deepfake risk (V1 stub with basic edge-sharpness heuristic)."""
        indicators: list[str] = []

        # Basic edge-sharpness analysis around faces (simplified)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        edges = cv2.Laplacian(gray, cv2.CV_64F)
        edge_var = float(np.var(edges))

        # Unusually sharp edges *could* indicate compositing (very rough heuristic)
        if edge_var > 5000:
            indicators.append("high_edge_variance")

        risk_score = min(edge_var / 10000.0, 0.5)  # cap at 0.5 for V1

        indicators.append("advanced_detection_requires_specialized_model")

        return {"risk_score": round(risk_score, 4), "indicators": indicators}

    async def watermark_image(
        self, image: np.ndarray, text: str = "VAF-GENERATED"
    ) -> np.ndarray:
        """Add a semi-transparent text watermark in the bottom-right corner."""
        result = image.copy()
        h, w = result.shape[:2]

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = max(0.4, min(w, h) / 600)
        thickness = max(1, int(font_scale * 2))

        (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
        margin = 10
        x = w - tw - margin
        y = h - margin

        # Create overlay for semi-transparency
        overlay = result.copy()
        cv2.putText(overlay, text, (x, y), font, font_scale, (255, 255, 255), thickness)
        alpha = 0.4
        cv2.addWeighted(overlay, alpha, result, 1 - alpha, 0, result)

        return result
