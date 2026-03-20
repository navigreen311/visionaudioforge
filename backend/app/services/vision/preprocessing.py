"""Vision preprocessing service with normalization, color spaces, and pipeline."""

from __future__ import annotations

import cv2
import numpy as np


class ImagePreprocessor:
    """OOP pipeline for image normalization, color conversion, and processing."""

    # ── Color-space conversion map ────────────────────────────────────
    _COLOR_CONVERSIONS: dict[tuple[str, str], int] = {
        ("rgb", "bgr"): cv2.COLOR_RGB2BGR,
        ("bgr", "rgb"): cv2.COLOR_BGR2RGB,
        ("rgb", "hsv"): cv2.COLOR_RGB2HSV,
        ("hsv", "rgb"): cv2.COLOR_HSV2RGB,
        ("bgr", "hsv"): cv2.COLOR_BGR2HSV,
        ("hsv", "bgr"): cv2.COLOR_HSV2BGR,
        ("rgb", "lab"): cv2.COLOR_RGB2LAB,
        ("lab", "rgb"): cv2.COLOR_LAB2RGB,
        ("bgr", "lab"): cv2.COLOR_BGR2LAB,
        ("lab", "bgr"): cv2.COLOR_LAB2BGR,
        ("rgb", "gray"): cv2.COLOR_RGB2GRAY,
        ("bgr", "gray"): cv2.COLOR_BGR2GRAY,
        ("gray", "rgb"): cv2.COLOR_GRAY2RGB,
        ("gray", "bgr"): cv2.COLOR_GRAY2BGR,
    }

    # ── Normalization ─────────────────────────────────────────────────

    @staticmethod
    def min_max_normalize(
        image: np.ndarray,
        target_range: tuple[float, float] = (0.0, 1.0),
    ) -> np.ndarray:
        """Scale pixel values to *target_range*. Returns float32."""
        img = image.astype(np.float32)
        lo, hi = float(img.min()), float(img.max())
        if lo == hi:
            # Constant image → map to lower bound of target range
            return np.full_like(img, target_range[0], dtype=np.float32)
        t_lo, t_hi = target_range
        return ((img - lo) / (hi - lo)) * (t_hi - t_lo) + t_lo

    @staticmethod
    def z_score_normalize(
        image: np.ndarray,
        global_stats: tuple[float, float] | None = None,
    ) -> np.ndarray:
        """Zero-mean, unit-variance normalization. Returns float32."""
        img = image.astype(np.float32)
        if global_stats is not None:
            mean, std = global_stats
        else:
            mean, std = float(img.mean()), float(img.std())
        if std == 0:
            return img - mean
        return (img - mean) / std

    @staticmethod
    def per_channel_normalize(image: np.ndarray) -> np.ndarray:
        """Independently z-score normalize each channel (axis 0,1)."""
        if image.ndim == 2:
            return ImagePreprocessor.z_score_normalize(image)
        img = image.astype(np.float32)
        for c in range(img.shape[2]):
            ch = img[:, :, c]
            mean, std = float(ch.mean()), float(ch.std())
            if std == 0:
                img[:, :, c] = ch - mean
            else:
                img[:, :, c] = (ch - mean) / std
        return img

    # ── Color-space conversion ────────────────────────────────────────

    @classmethod
    def convert_color_space(
        cls,
        image: np.ndarray,
        from_space: str,
        to_space: str,
    ) -> np.ndarray:
        """Convert between rgb, bgr, hsv, lab, gray."""
        src = from_space.lower()
        dst = to_space.lower()
        if src == dst:
            return image.copy()

        key = (src, dst)
        if key not in cls._COLOR_CONVERSIONS:
            raise ValueError(
                f"Unsupported conversion: {src} -> {dst}. "
                f"Supported pairs: {list(cls._COLOR_CONVERSIONS.keys())}"
            )

        # Validate input channels
        expected = 1 if src == "gray" else 3
        actual = 1 if image.ndim == 2 else image.shape[2]
        if actual != expected:
            raise ValueError(
                f"Expected {expected} channel(s) for '{src}', got {actual}"
            )

        return cv2.cvtColor(image, cls._COLOR_CONVERSIONS[key])

    # ── Histogram equalization ────────────────────────────────────────

    @staticmethod
    def histogram_equalization(image: np.ndarray) -> np.ndarray:
        """Equalize histogram. Color images: equalize L channel in LAB."""
        if image.ndim == 2:
            return cv2.equalizeHist(image)

        # Color: convert to LAB, equalize L, convert back
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        lab[:, :, 0] = cv2.equalizeHist(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    # ── Edge detection ────────────────────────────────────────────────

    @staticmethod
    def edge_detection(
        image: np.ndarray,
        method: str = "canny",
        low: int = 50,
        high: int = 150,
    ) -> np.ndarray:
        """Detect edges using canny, sobel, or laplacian."""
        # Convert to grayscale if needed
        if image.ndim == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        method = method.lower()
        if method == "canny":
            return cv2.Canny(gray, low, high)
        elif method == "sobel":
            sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            mag = np.sqrt(sx**2 + sy**2)
            return np.clip(mag, 0, 255).astype(np.uint8)
        elif method == "laplacian":
            lap = cv2.Laplacian(gray, cv2.CV_64F)
            return np.clip(np.abs(lap), 0, 255).astype(np.uint8)
        else:
            raise ValueError(f"Unsupported edge method: {method}. Use canny, sobel, or laplacian.")

    # ── Resize ────────────────────────────────────────────────────────

    @staticmethod
    def resize(
        image: np.ndarray,
        width: int,
        height: int,
        maintain_aspect: bool = True,
    ) -> np.ndarray:
        """Resize image. If *maintain_aspect*, letterbox with black padding."""
        if not maintain_aspect:
            return cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)

        h, w = image.shape[:2]
        scale = min(width / w, height / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Create canvas and center the resized image
        if image.ndim == 3:
            canvas = np.zeros((height, width, image.shape[2]), dtype=image.dtype)
        else:
            canvas = np.zeros((height, width), dtype=image.dtype)

        y_off = (height - new_h) // 2
        x_off = (width - new_w) // 2
        canvas[y_off : y_off + new_h, x_off : x_off + new_w] = resized
        return canvas

    # ── Pipeline ──────────────────────────────────────────────────────

    def preprocess_pipeline(
        self,
        image: np.ndarray,
        steps: list[dict],
    ) -> np.ndarray:
        """Execute a list of preprocessing steps sequentially.

        Each step: ``{"op": "<operation>", "params": {<kwargs>}}``

        Supported ops:
            normalize (method: min_max | z_score | per_channel),
            color_space (from, to), histogram_equalization,
            edge_detection (method, low, high),
            resize (width, height, maintain_aspect)
        """
        result = image.copy()
        for step in steps:
            op = step.get("op", "")
            params = step.get("params", {})
            result = self._dispatch(op, result, params)
        return result

    # ── Internal dispatch ─────────────────────────────────────────────

    def _dispatch(self, op: str, image: np.ndarray, params: dict) -> np.ndarray:
        if op == "normalize":
            method = params.get("method", "min_max")
            if method == "min_max":
                return self.min_max_normalize(image, params.get("target_range", (0, 1)))
            elif method == "z_score":
                return self.z_score_normalize(image, params.get("global_stats"))
            elif method == "per_channel":
                return self.per_channel_normalize(image)
            else:
                raise ValueError(f"Unknown normalize method: {method}")
        elif op == "color_space":
            return self.convert_color_space(
                image,
                params.get("from", "rgb"),
                params.get("to", "rgb"),
            )
        elif op == "histogram_equalization":
            return self.histogram_equalization(image)
        elif op == "edge_detection":
            return self.edge_detection(
                image,
                method=params.get("method", "canny"),
                low=params.get("low", 50),
                high=params.get("high", 150),
            )
        elif op == "resize":
            return self.resize(
                image,
                width=params["width"],
                height=params["height"],
                maintain_aspect=params.get("maintain_aspect", True),
            )
        else:
            raise ValueError(f"Unknown pipeline operation: {op}")
