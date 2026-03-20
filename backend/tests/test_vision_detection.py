"""Tests for vision detection, OCR, and error analysis services + API routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.vision.detection import ObjectDetector
from app.services.vision.error_analysis import (
    class_level_metrics,
    compute_confusion_matrix,
    generate_quality_report,
    identify_top_confusions,
)
from app.services.vision.ocr import OCREngine


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _synthetic_image(width: int = 64, height: int = 64) -> np.ndarray:
    """Create a simple BGR test image."""
    return np.zeros((height, width, 3), dtype=np.uint8)


def _png_bytes(image: np.ndarray | None = None) -> bytes:
    """Encode an image (or a synthetic one) to PNG bytes."""
    import cv2

    if image is None:
        image = _synthetic_image()
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


# ------------------------------------------------------------------
# Detection tests
# ------------------------------------------------------------------

class TestObjectDetector:
    def test_detection_returns_list(self):
        """detect() should return a list even when no model is loaded."""
        detector = ObjectDetector()
        # Without ultralytics installed (or with it), result must be a list
        result = detector.detect(_synthetic_image())
        assert isinstance(result, list)

    def test_detection_handles_missing_model(self):
        """When ultralytics is not importable, detect returns [] gracefully."""
        detector = ObjectDetector()
        detector._model = None
        detector._available = True  # reset so _load_model tries again

        with patch.dict("sys.modules", {"ultralytics": None}):
            with patch("builtins.__import__", side_effect=ImportError("no ultralytics")):
                detector._model = None  # force re-load attempt
                detector._available = True
                result = detector.detect(_synthetic_image())
                assert result == []

    def test_detect_batch_returns_list_of_lists(self):
        """detect_batch should return one list per image."""
        detector = ObjectDetector()
        images = [_synthetic_image(), _synthetic_image()]
        results = detector.detect_batch(images)
        assert isinstance(results, list)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, list)

    def test_draw_detections_returns_image(self):
        """draw_detections should return an ndarray of the same shape."""
        detector = ObjectDetector()
        img = _synthetic_image(100, 100)
        detections = [
            {"bbox": [10, 10, 50, 50], "class_id": 0, "class_name": "cat", "confidence": 0.9}
        ]
        result = detector.draw_detections(img, detections)
        assert isinstance(result, np.ndarray)
        assert result.shape == img.shape


# ------------------------------------------------------------------
# OCR tests
# ------------------------------------------------------------------

class TestOCREngine:
    def test_ocr_returns_text_structure(self):
        """extract_text should return a dict with expected keys."""
        engine = OCREngine()
        result = engine.extract_text(_synthetic_image())
        assert "full_text" in result
        assert "blocks" in result
        assert isinstance(result["blocks"], list)
        # If pytesseract is missing, we get an error key
        if not engine._available:
            assert result.get("error") == "OCR engine not installed"
            assert result["language"] == "unknown"


# ------------------------------------------------------------------
# Error analysis tests
# ------------------------------------------------------------------

class TestErrorAnalysis:
    CLASSES = ["cat", "dog", "bird"]
    Y_TRUE = ["cat", "cat", "dog", "dog", "bird", "bird", "cat", "dog", "bird"]
    Y_PRED = ["cat", "dog", "dog", "dog", "bird", "cat",  "cat", "bird", "bird"]

    def test_confusion_matrix_shape(self):
        """3 classes should produce a 3x3 matrix."""
        cm = compute_confusion_matrix(self.Y_TRUE, self.Y_PRED, self.CLASSES)
        assert cm.shape == (3, 3)

    def test_confusion_matrix_values(self):
        """Verify specific cells of the confusion matrix."""
        cm = compute_confusion_matrix(self.Y_TRUE, self.Y_PRED, self.CLASSES)
        # cat row: 2 true cats → predicted cat=2, dog=1  (3 cat samples)
        assert cm[0, 0] == 2  # cat→cat
        assert cm[0, 1] == 1  # cat→dog

    def test_class_metrics_precision_recall(self):
        """Verify precision/recall math for a known confusion matrix."""
        cm = np.array([[5, 0, 0], [1, 3, 1], [0, 0, 4]])
        names = ["A", "B", "C"]
        metrics = class_level_metrics(cm, names)
        # Class A: TP=5, col_sum=6, row_sum=5 → precision=5/6, recall=5/5
        assert metrics[0]["class"] == "A"
        assert abs(metrics[0]["precision"] - 5 / 6) < 0.001
        assert metrics[0]["recall"] == 1.0
        # Class C: TP=4, col_sum=5, row_sum=4 → precision=4/5, recall=4/4
        assert abs(metrics[2]["precision"] - 0.8) < 0.001
        assert metrics[2]["recall"] == 1.0

    def test_top_confusions_sorted(self):
        """Top confusions should be sorted by count descending."""
        cm = np.array([[5, 3, 1], [2, 4, 0], [0, 1, 6]])
        names = ["A", "B", "C"]
        top = identify_top_confusions(cm, names, top_k=5)
        counts = [c["count"] for c in top]
        assert counts == sorted(counts, reverse=True)
        # Highest confusion: A→B with 3
        assert top[0]["true_class"] == "A"
        assert top[0]["predicted_class"] == "B"
        assert top[0]["count"] == 3

    def test_quality_report_complete(self):
        """generate_quality_report should include all expected keys."""
        report = generate_quality_report(self.Y_TRUE, self.Y_PRED, self.CLASSES)
        assert "confusion_matrix" in report
        assert "per_class" in report
        assert "overall" in report
        assert "top_confusions" in report
        assert "total_samples" in report
        assert "error_rate" in report
        assert report["total_samples"] == len(self.Y_TRUE)
        assert 0.0 <= report["error_rate"] <= 1.0


# ------------------------------------------------------------------
# API route tests
# ------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_api_detect_endpoint(client: AsyncClient):
    """POST /api/vision/detect should return detection results."""
    png = _png_bytes()
    response = await client.post(
        "/api/vision/detect",
        files={"file": ("test.png", png, "image/png")},
        params={"confidence": 0.5},
    )
    assert response.status_code == 200
    data = response.json()
    assert "detections" in data
    assert "count" in data
    assert "visualization" in data
    assert "processing_time_ms" in data
    assert isinstance(data["detections"], list)


@pytest.mark.anyio
async def test_api_ocr_endpoint(client: AsyncClient):
    """POST /api/vision/ocr should return OCR results."""
    png = _png_bytes()
    response = await client.post(
        "/api/vision/ocr",
        files={"file": ("test.png", png, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "full_text" in data
    assert "processing_time_ms" in data


@pytest.mark.anyio
async def test_api_error_analysis_endpoint(client: AsyncClient):
    """POST /api/vision/error-analysis should return a quality report."""
    payload = {
        "predictions": ["cat", "dog", "cat"],
        "ground_truth": ["cat", "cat", "cat"],
        "classes": ["cat", "dog"],
    }
    response = await client.post("/api/vision/error-analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "confusion_matrix" in data
    assert "per_class" in data
    assert "overall" in data
    assert "total_samples" in data
    assert data["total_samples"] == 3
