"""Tests for depth estimation, anomaly detection, face/plate detection,
and screen intelligence services + API routes."""

from __future__ import annotations

import numpy as np
import pytest
import cv2
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.vision.depth import DepthEstimator
from app.services.vision.anomaly import AnomalyDetector
from app.services.vision.face_plate import FacePlateDetector
from app.services.vision.screen_intel import ScreenIntelligence


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _synthetic_image(width: int = 64, height: int = 64, color: tuple = (128, 128, 128)) -> np.ndarray:
    """Create a simple BGR test image filled with a solid color."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = color
    return img


def _synthetic_gradient_image(width: int = 64, height: int = 64) -> np.ndarray:
    """Create a BGR image with a horizontal gradient (edges for depth)."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for x in range(width):
        val = int((x / width) * 255)
        img[:, x] = (val, val, val)
    # Add some edges/features
    cv2.rectangle(img, (10, 10), (30, 30), (255, 255, 255), 2)
    cv2.circle(img, (50, 40), 10, (0, 0, 255), -1)
    return img


def _dark_image(width: int = 64, height: int = 64) -> np.ndarray:
    """Create a very dark image (mean < 20)."""
    return np.full((height, width, 3), 5, dtype=np.uint8)


def _bright_image(width: int = 64, height: int = 64) -> np.ndarray:
    """Create a very bright image (mean > 235)."""
    return np.full((height, width, 3), 250, dtype=np.uint8)


def _png_bytes(image: np.ndarray | None = None) -> bytes:
    """Encode an image to PNG bytes."""
    if image is None:
        image = _synthetic_image()
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


# ------------------------------------------------------------------
# Depth estimation tests
# ------------------------------------------------------------------

class TestDepthEstimator:
    def test_depth_map_shape_matches_input(self):
        """Depth map should have same H x W as input image."""
        estimator = DepthEstimator()
        img = _synthetic_gradient_image(80, 60)
        result = estimator.estimate_depth(img)
        assert result["depth_map"].shape == (60, 80)

    def test_depth_normalized_0_to_1(self):
        """Depth map values should be in [0, 1] range."""
        estimator = DepthEstimator()
        img = _synthetic_gradient_image(100, 100)
        result = estimator.estimate_depth(img)
        depth_map = result["depth_map"]
        assert depth_map.dtype == np.float32
        assert float(depth_map.min()) >= 0.0
        assert float(depth_map.max()) <= 1.0

    def test_depth_visualization_is_color(self):
        """Visualization should be a 3-channel color image."""
        estimator = DepthEstimator()
        img = _synthetic_gradient_image()
        result = estimator.estimate_depth(img)
        vis = result["visualization"]
        assert len(vis.shape) == 3
        assert vis.shape[2] == 3

    def test_depth_min_max_values(self):
        """min_depth and max_depth should be floats in [0, 1]."""
        estimator = DepthEstimator()
        img = _synthetic_gradient_image()
        result = estimator.estimate_depth(img)
        assert 0.0 <= result["min_depth"] <= 1.0
        assert 0.0 <= result["max_depth"] <= 1.0

    def test_pointcloud_stub(self):
        """Point cloud stub should return point count and note."""
        estimator = DepthEstimator()
        depth_map = np.zeros((100, 100), dtype=np.float32)
        result = estimator.depth_to_pointcloud_stub(depth_map)
        assert result["points"] == 10000
        assert "camera calibration" in result["note"]


# ------------------------------------------------------------------
# Anomaly detection tests
# ------------------------------------------------------------------

class TestAnomalyDetector:
    def test_anomaly_detects_dark_image(self):
        """A very dark image should be flagged as anomalous."""
        detector = AnomalyDetector()
        img = _dark_image()
        result = detector.detect_anomaly(img)
        assert result["is_anomaly"] is True
        assert result["anomaly_score"] > 0.3
        assert "dark" in result["reason"].lower()

    def test_anomaly_normal_image_passes(self):
        """A normal image should not be flagged as anomalous."""
        detector = AnomalyDetector()
        # Use gradient image with varied pixel values to avoid low-contrast flag
        img = _synthetic_gradient_image(64, 64)
        result = detector.detect_anomaly(img)
        assert result["is_anomaly"] is False
        assert result["anomaly_score"] <= 0.3
        assert result["reason"] == "Normal"

    def test_anomaly_bright_image(self):
        """A very bright image should be flagged."""
        detector = AnomalyDetector()
        img = _bright_image()
        result = detector.detect_anomaly(img)
        assert result["is_anomaly"] is True
        assert "bright" in result["reason"].lower()

    def test_anomaly_batch(self):
        """Batch detection should return one result per image."""
        detector = AnomalyDetector()
        images = [_synthetic_image(), _dark_image(), _bright_image()]
        results = detector.detect_anomaly_batch(images)
        assert len(results) == 3
        for r in results:
            assert "is_anomaly" in r
            assert "anomaly_score" in r

    def test_build_reference_stats(self):
        """Reference stats should include mean, std, and histogram."""
        detector = AnomalyDetector()
        images = [_synthetic_image(color=(100, 100, 100)) for _ in range(5)]
        stats = detector.build_reference_stats(images)
        assert "mean" in stats
        assert "std" in stats
        assert "histogram" in stats
        assert len(stats["histogram"]) == 256


# ------------------------------------------------------------------
# Face & plate detection tests
# ------------------------------------------------------------------

class TestFacePlateDetector:
    def test_face_detection_returns_list(self):
        """detect_faces should return a list of detections."""
        detector = FacePlateDetector()
        img = _synthetic_image(200, 200)
        result = detector.detect_faces(img)
        assert isinstance(result, list)

    def test_plate_detection_returns_list(self):
        """detect_license_plates should return a list."""
        detector = FacePlateDetector()
        img = _synthetic_image(200, 200)
        result = detector.detect_license_plates(img)
        assert isinstance(result, list)

    def test_blur_regions_modifies_image(self):
        """blur_regions should return a modified image."""
        detector = FacePlateDetector()
        img = _synthetic_gradient_image(100, 100)
        regions = [[10, 10, 30, 30]]
        result = detector.blur_regions(img, regions)
        assert isinstance(result, np.ndarray)
        assert result.shape == img.shape
        # The blurred region should differ from the original
        roi_orig = img[10:40, 10:40]
        roi_blurred = result[10:40, 10:40]
        assert not np.array_equal(roi_orig, roi_blurred)

    def test_blur_regions_pixelate(self):
        """blur_regions with pixelate method should also work."""
        detector = FacePlateDetector()
        img = _synthetic_gradient_image(100, 100)
        regions = [[10, 10, 30, 30]]
        result = detector.blur_regions(img, regions, method="pixelate")
        assert isinstance(result, np.ndarray)
        assert result.shape == img.shape

    def test_draw_detections_returns_image(self):
        """draw_detections should return an annotated image."""
        detector = FacePlateDetector()
        img = _synthetic_image(100, 100)
        faces = [{"bbox": [10, 10, 30, 30], "confidence": 0.9}]
        plates = [{"bbox": [50, 50, 40, 15], "confidence": 0.7, "text": "ABC123"}]
        result = detector.draw_detections(img, faces=faces, plates=plates)
        assert isinstance(result, np.ndarray)
        assert result.shape == img.shape


# ------------------------------------------------------------------
# Screen intelligence tests
# ------------------------------------------------------------------

class TestScreenIntelligence:
    def test_screen_intel_returns_analysis(self):
        """analyze_screenshot should return all expected keys."""
        intel = ScreenIntelligence()
        img = _synthetic_gradient_image(200, 150)
        result = intel.analyze_screenshot(img)
        assert "ui_elements" in result
        assert "text_content" in result
        assert "brightness" in result
        assert "edge_density" in result
        assert "dominant_colors" in result
        assert "layout_type" in result
        assert isinstance(result["brightness"], float)
        assert isinstance(result["edge_density"], float)
        assert isinstance(result["dominant_colors"], list)

    def test_ui_element_detection(self):
        """detect_ui_elements should return a list of elements."""
        intel = ScreenIntelligence()
        # Create image with rectangle-like UI elements
        img = np.ones((300, 400, 3), dtype=np.uint8) * 240
        # Draw button-like rectangles
        cv2.rectangle(img, (50, 50), (150, 80), (100, 100, 100), 2)
        cv2.rectangle(img, (50, 100), (250, 120), (100, 100, 100), 2)
        cv2.rectangle(img, (200, 200), (380, 280), (50, 50, 50), -1)
        result = intel.detect_ui_elements(img)
        assert isinstance(result, list)
        for elem in result:
            assert "type" in elem
            assert "bbox" in elem
            assert "confidence" in elem
            assert elem["type"] in ("button", "input", "menu", "text", "image")

    def test_parse_chart_returns_structure(self):
        """parse_chart should return chart metadata."""
        intel = ScreenIntelligence()
        img = _synthetic_image(200, 200)
        result = intel.parse_chart(img)
        assert "chart_type" in result
        assert "has_axes" in result
        assert "data_regions" in result

    def test_track_cursor_returns_positions(self):
        """track_cursor should return one result per frame."""
        intel = ScreenIntelligence()
        frames = [_synthetic_image(100, 100) for _ in range(3)]
        result = intel.track_cursor(frames)
        assert len(result) == 3
        for r in result:
            assert "frame" in r
            assert "position" in r
            assert "clicked" in r


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
async def test_api_depth(client: AsyncClient):
    """POST /api/vision/depth should return depth estimation results."""
    png = _png_bytes(_synthetic_gradient_image())
    response = await client.post(
        "/api/vision/depth",
        files={"file": ("test.png", png, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "min_depth" in data
    assert "max_depth" in data
    assert "depth_map_shape" in data
    assert "visualization" in data
    assert "processing_time_ms" in data


@pytest.mark.anyio
async def test_api_anomaly(client: AsyncClient):
    """POST /api/vision/anomaly should return anomaly detection results."""
    png = _png_bytes(_synthetic_image())
    response = await client.post(
        "/api/vision/anomaly",
        files={"file": ("test.png", png, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "is_anomaly" in data
    assert "anomaly_score" in data
    assert "anomaly_regions" in data
    assert "reason" in data
    assert "processing_time_ms" in data


@pytest.mark.anyio
async def test_api_faces(client: AsyncClient):
    """POST /api/vision/faces should return face detection results."""
    png = _png_bytes(_synthetic_image(200, 200))
    response = await client.post(
        "/api/vision/faces",
        files={"file": ("test.png", png, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "faces" in data
    assert "count" in data
    assert "visualization" in data
    assert "processing_time_ms" in data
    assert isinstance(data["faces"], list)


@pytest.mark.anyio
async def test_api_plates(client: AsyncClient):
    """POST /api/vision/plates should return plate detection results."""
    png = _png_bytes(_synthetic_image(200, 200))
    response = await client.post(
        "/api/vision/plates",
        files={"file": ("test.png", png, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "plates" in data
    assert "count" in data
    assert "visualization" in data


@pytest.mark.anyio
async def test_api_screen_intel(client: AsyncClient):
    """POST /api/vision/screen-intel should return screen analysis."""
    png = _png_bytes(_synthetic_gradient_image(200, 150))
    response = await client.post(
        "/api/vision/screen-intel",
        files={"file": ("test.png", png, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "ui_elements" in data
    assert "brightness" in data
    assert "edge_density" in data
    assert "dominant_colors" in data
    assert "layout_type" in data
    assert "processing_time_ms" in data


@pytest.mark.anyio
async def test_api_screen_analyze_redirects(client: AsyncClient):
    """POST /api/vision/screen-analyze should now work (not 501)."""
    png = _png_bytes(_synthetic_image())
    response = await client.post(
        "/api/vision/screen-analyze",
        files={"file": ("test.png", png, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "brightness" in data
