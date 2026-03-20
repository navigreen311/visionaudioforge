"""Tests for the vision preprocessing service."""

import numpy as np
import pytest

from app.services.vision.preprocessing import ImagePreprocessor
from app.services.vision.utils import (
    base64_to_image,
    image_to_base64,
    validate_image,
)


@pytest.fixture
def preprocessor():
    return ImagePreprocessor()


@pytest.fixture
def rgb_image():
    """Random 100x100 RGB uint8 test image."""
    return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)


@pytest.fixture
def gray_image():
    """Random 100x100 grayscale uint8 test image."""
    return np.random.randint(0, 255, (100, 100), dtype=np.uint8)


# ── Normalization ─────────────────────────────────────────────────────


def test_min_max_normalizes_to_0_1(rgb_image):
    out = ImagePreprocessor.min_max_normalize(rgb_image)
    assert out.dtype == np.float32
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_min_max_constant_image():
    """Edge case: all pixels identical."""
    img = np.full((10, 10, 3), 128, dtype=np.uint8)
    out = ImagePreprocessor.min_max_normalize(img)
    assert out.min() == 0.0
    assert out.max() == 0.0


def test_z_score_has_zero_mean(rgb_image):
    out = ImagePreprocessor.z_score_normalize(rgb_image)
    assert abs(float(out.mean())) < 0.01


def test_z_score_with_global_stats(rgb_image):
    out = ImagePreprocessor.z_score_normalize(rgb_image, global_stats=(100.0, 50.0))
    expected_mean = (rgb_image.astype(np.float32).mean() - 100.0) / 50.0
    assert abs(float(out.mean()) - expected_mean) < 0.01


def test_per_channel_normalize(rgb_image):
    out = ImagePreprocessor.per_channel_normalize(rgb_image)
    for c in range(3):
        ch = out[:, :, c]
        assert abs(float(ch.mean())) < 0.01


# ── Color-space conversion ───────────────────────────────────────────


def test_color_space_rgb_to_hsv(rgb_image):
    out = ImagePreprocessor.convert_color_space(rgb_image, "rgb", "hsv")
    assert out.shape == rgb_image.shape


def test_color_space_rgb_to_gray(rgb_image):
    out = ImagePreprocessor.convert_color_space(rgb_image, "rgb", "gray")
    assert out.ndim == 2


def test_color_space_invalid_raises():
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="Unsupported conversion"):
        ImagePreprocessor.convert_color_space(img, "rgb", "xyz")


# ── Edge detection ────────────────────────────────────────────────────


def test_edge_detection_canny(rgb_image):
    out = ImagePreprocessor.edge_detection(rgb_image, method="canny")
    assert out.ndim == 2
    unique = set(np.unique(out))
    assert unique.issubset({0, 255})


def test_edge_detection_sobel(rgb_image):
    out = ImagePreprocessor.edge_detection(rgb_image, method="sobel")
    assert out.ndim == 2
    assert out.dtype == np.uint8


# ── Histogram equalization ────────────────────────────────────────────


def test_histogram_equalization_gray(gray_image):
    out = ImagePreprocessor.histogram_equalization(gray_image)
    assert out.shape == gray_image.shape
    assert int(out.min()) >= 0
    assert int(out.max()) <= 255


def test_histogram_equalization_color(rgb_image):
    out = ImagePreprocessor.histogram_equalization(rgb_image)
    assert out.shape == rgb_image.shape


# ── Resize ────────────────────────────────────────────────────────────


def test_resize_maintain_aspect(rgb_image):
    out = ImagePreprocessor.resize(rgb_image, 200, 200, maintain_aspect=True)
    assert out.shape[0] == 200
    assert out.shape[1] == 200


# ── Pipeline ──────────────────────────────────────────────────────────


def test_pipeline_chains_operations(preprocessor, rgb_image):
    steps = [
        {"op": "normalize", "params": {"method": "min_max"}},
        {"op": "color_space", "params": {"from": "rgb", "to": "hsv"}},
    ]
    out = preprocessor.preprocess_pipeline(rgb_image, steps)
    assert out is not None
    assert out.shape[:2] == rgb_image.shape[:2]


# ── Utils ─────────────────────────────────────────────────────────────


def test_image_to_base64_roundtrip(rgb_image):
    b64 = image_to_base64(rgb_image, fmt="png")
    decoded = base64_to_image(b64)
    # cv2 reads as BGR; original is RGB — compare shapes & rough values
    assert decoded.shape == rgb_image.shape


def test_validate_image_rejects_invalid():
    with pytest.raises(ValueError, match="Unable to decode"):
        validate_image(b"not-an-image")


def test_validate_image_rejects_oversized():
    big = b"\x00" * (11 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds limit"):
        validate_image(big)
