"""High-level vision service: histogram, blur, brightness, contrast, rotation, flip."""

from __future__ import annotations

import cv2
import numpy as np


class VisionService:
    """Stateless image manipulation utilities built on OpenCV."""

    # ------------------------------------------------------------------
    # Histogram
    # ------------------------------------------------------------------

    @staticmethod
    def compute_histogram(image: np.ndarray) -> dict[str, list[int]]:
        """Compute per-channel RGB histogram (256 bins each).

        Parameters
        ----------
        image : np.ndarray
            BGR or RGB image (3-channel uint8).

        Returns
        -------
        dict with keys ``r``, ``g``, ``b`` each mapping to a list of 256 counts.
        """
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Expected a 3-channel colour image for histogram computation.")

        histograms: dict[str, list[int]] = {}
        # OpenCV default channel order is BGR
        channel_names = ("b", "g", "r")
        for idx, name in enumerate(channel_names):
            hist = cv2.calcHist([image], [idx], None, [256], [0, 256])
            histograms[name] = hist.flatten().astype(int).tolist()

        return histograms

    # ------------------------------------------------------------------
    # Blur
    # ------------------------------------------------------------------

    @staticmethod
    def blur(
        image: np.ndarray,
        method: str = "gaussian",
        kernel_size: int = 5,
    ) -> np.ndarray:
        """Apply blur to an image.

        Parameters
        ----------
        method : str
            One of ``gaussian``, ``median``, ``bilateral``.
        kernel_size : int
            Must be a positive odd integer.
        """
        if kernel_size < 1 or kernel_size % 2 == 0:
            raise ValueError("kernel_size must be a positive odd integer.")

        method = method.lower()
        if method == "gaussian":
            return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        elif method == "median":
            return cv2.medianBlur(image, kernel_size)
        elif method == "bilateral":
            return cv2.bilateralFilter(image, kernel_size, 75, 75)
        else:
            raise ValueError(f"Unsupported blur method: {method}. Use gaussian, median, or bilateral.")

    # ------------------------------------------------------------------
    # Brightness
    # ------------------------------------------------------------------

    @staticmethod
    def adjust_brightness(image: np.ndarray, value: int = 0) -> np.ndarray:
        """Adjust brightness by adding *value* to all pixels.

        Parameters
        ----------
        value : int
            Brightness offset in range ``[-100, 100]``.
        """
        value = max(-100, min(100, value))
        if value == 0:
            return image.copy()

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.int16)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] + value, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # ------------------------------------------------------------------
    # Contrast
    # ------------------------------------------------------------------

    @staticmethod
    def adjust_contrast(image: np.ndarray, factor: float = 1.0) -> np.ndarray:
        """Adjust contrast by multiplying pixel deviations from the mean.

        Parameters
        ----------
        factor : float
            Contrast multiplier in range ``[0.1, 3.0]``.
        """
        factor = max(0.1, min(3.0, factor))
        if factor == 1.0:
            return image.copy()

        img_f = image.astype(np.float32)
        mean = img_f.mean()
        adjusted = mean + factor * (img_f - mean)
        return np.clip(adjusted, 0, 255).astype(np.uint8)

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------

    @staticmethod
    def rotate(image: np.ndarray, angle: int = 0) -> np.ndarray:
        """Rotate image.

        Parameters
        ----------
        angle : int
            One of ``0``, ``90``, ``180``, ``270`` for fast rotation,
            or any other integer for arbitrary-angle rotation (with border fill).
        """
        if angle == 0:
            return image.copy()
        if angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        if angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        if angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Arbitrary angle
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)

        # Compute new bounding size
        cos_a = abs(matrix[0, 0])
        sin_a = abs(matrix[0, 1])
        new_w = int(h * sin_a + w * cos_a)
        new_h = int(h * cos_a + w * sin_a)

        matrix[0, 2] += (new_w - w) / 2
        matrix[1, 2] += (new_h - h) / 2

        return cv2.warpAffine(image, matrix, (new_w, new_h), borderValue=(0, 0, 0))

    # ------------------------------------------------------------------
    # Flip
    # ------------------------------------------------------------------

    @staticmethod
    def flip(image: np.ndarray, mode: str = "none") -> np.ndarray:
        """Flip image.

        Parameters
        ----------
        mode : str
            ``none`` — no-op, ``h`` — horizontal, ``v`` — vertical, ``both`` — both axes.
        """
        mode = mode.lower()
        if mode == "none":
            return image.copy()
        if mode == "h":
            return cv2.flip(image, 1)
        if mode == "v":
            return cv2.flip(image, 0)
        if mode == "both":
            return cv2.flip(image, -1)
        raise ValueError(f"Unsupported flip mode: {mode}. Use none, h, v, or both.")
