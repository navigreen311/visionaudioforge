"""Vision utility helpers: encoding, decoding, stats, validation."""

from __future__ import annotations

import base64

import cv2
import numpy as np


def image_to_base64(image: np.ndarray, fmt: str = "png") -> str:
    """Encode a numpy image to a base64 string."""
    ext = f".{fmt}"
    success, buf = cv2.imencode(ext, image)
    if not success:
        raise ValueError(f"Failed to encode image as {fmt}")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def base64_to_image(b64_string: str) -> np.ndarray:
    """Decode a base64 string back to a numpy image."""
    data = base64.b64decode(b64_string)
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode base64 string to image")
    return image


def calculate_image_stats(image: np.ndarray) -> dict:
    """Return per-channel mean, std, min, max plus shape and dtype."""
    stats: dict = {
        "shape": list(image.shape),
        "dtype": str(image.dtype),
    }

    if image.ndim == 2:
        # Grayscale
        stats["channels"] = [
            {
                "mean": float(image.mean()),
                "std": float(image.std()),
                "min": float(image.min()),
                "max": float(image.max()),
            }
        ]
    else:
        channels = []
        for c in range(image.shape[2]):
            ch = image[:, :, c]
            channels.append(
                {
                    "mean": float(ch.mean()),
                    "std": float(ch.std()),
                    "min": float(ch.min()),
                    "max": float(ch.max()),
                }
            )
        stats["channels"] = channels

    return stats


def validate_image(file_bytes: bytes, max_size_mb: float = 10) -> np.ndarray:
    """Validate and decode raw file bytes into a numpy image.

    Raises ``ValueError`` on invalid/oversized input.
    """
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(f"Image size {size_mb:.1f} MB exceeds limit of {max_size_mb} MB")

    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode image from provided bytes")

    if image.ndim < 2:
        raise ValueError(f"Invalid image shape: {image.shape}")

    return image
