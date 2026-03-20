"""Tests for optical flow and frame differencing services + API endpoints."""

from __future__ import annotations

import io

import cv2
import numpy as np
import pytest

from app.services.vision.motion import MotionAnalyzer
from app.services.vision.visualization import create_flow_visualization, create_motion_heatmap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_test_frame_pair(
    width: int = 200,
    height: int = 200,
    rect_size: int = 40,
    shift: int = 30,
) -> tuple[np.ndarray, np.ndarray]:
    """Create two grayscale frames with a white rectangle that moves."""
    frame1 = np.zeros((height, width), dtype=np.uint8)
    frame2 = np.zeros((height, width), dtype=np.uint8)

    x, y = 60, 60
    cv2.rectangle(frame1, (x, y), (x + rect_size, y + rect_size), 255, -1)
    cv2.rectangle(frame2, (x + shift, y + shift), (x + shift + rect_size, y + shift + rect_size), 255, -1)

    return frame1, frame2


def _encode_frame_as_png(gray: np.ndarray) -> bytes:
    """Encode a grayscale frame as PNG bytes (for upload simulation)."""
    bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR) if len(gray.shape) == 2 else gray
    _, buf = cv2.imencode(".png", bgr)
    return buf.tobytes()


# ---------------------------------------------------------------------------
# Unit tests — MotionAnalyzer
# ---------------------------------------------------------------------------

analyzer = MotionAnalyzer()


def test_lucas_kanade_detects_motion():
    prev, curr = create_test_frame_pair()
    result = analyzer.lucas_kanade(prev, curr)

    assert result["mean_magnitude"] > 0, "LK should detect motion between shifted rectangles"
    assert result["num_tracked"] > 0


def test_farneback_returns_dense_flow():
    prev, curr = create_test_frame_pair()
    result = analyzer.farneback_dense(prev, curr)

    h, w = prev.shape[:2]
    assert result["flow"].shape == (h, w, 2), "Flow array should be (h, w, 2)"
    assert result["mean_magnitude"] >= 0
    assert result["max_magnitude"] >= result["mean_magnitude"]


def test_frame_diff_detects_changes():
    prev, curr = create_test_frame_pair()
    result = analyzer.frame_diff_consecutive(prev, curr)

    assert result["motion_percentage"] > 0, "Should detect motion between different frames"
    assert result["motion_pixels"] > 0
    assert result["total_pixels"] == prev.shape[0] * prev.shape[1]


def test_frame_diff_no_motion():
    frame = np.zeros((100, 100), dtype=np.uint8)
    cv2.rectangle(frame, (20, 20), (60, 60), 255, -1)

    result = analyzer.frame_diff_consecutive(frame, frame)

    assert result["motion_percentage"] == pytest.approx(0.0, abs=0.01), \
        "Identical frames should produce ~0% motion"


def test_three_frame_diff():
    f1 = np.zeros((200, 200), dtype=np.uint8)
    f2 = np.zeros((200, 200), dtype=np.uint8)
    f3 = np.zeros((200, 200), dtype=np.uint8)

    # Object moves through frames
    cv2.rectangle(f1, (30, 30), (70, 70), 255, -1)
    cv2.rectangle(f2, (60, 60), (100, 100), 255, -1)
    cv2.rectangle(f3, (90, 90), (130, 130), 255, -1)

    result = analyzer.frame_diff_three_frame(f1, f2, f3)

    assert result["motion_percentage"] > 0, "Three-frame diff should detect motion"
    assert result["motion_mask"].shape == (200, 200)


def test_compute_motion_stats_dense():
    prev, curr = create_test_frame_pair()
    flow_result = analyzer.farneback_dense(prev, curr)
    stats = analyzer.compute_motion_stats(flow_result)

    assert "mean_magnitude" in stats
    assert "max_magnitude" in stats
    assert "motion_area_pct" in stats
    assert "dominant_direction_deg" in stats


# ---------------------------------------------------------------------------
# Unit tests — Visualization
# ---------------------------------------------------------------------------

def test_motion_heatmap_shape():
    prev, curr = create_test_frame_pair()
    flow_result = analyzer.farneback_dense(prev, curr)
    heatmap = create_motion_heatmap(flow_result["flow"])

    assert heatmap.shape == (200, 200, 3), "Heatmap should be a 3-channel image"
    assert heatmap.dtype == np.uint8


def test_flow_visualization_rgb():
    prev, curr = create_test_frame_pair()
    flow_result = analyzer.farneback_dense(prev, curr)
    rgb = create_flow_visualization(flow_result["flow"])

    assert rgb.shape == (200, 200, 3)


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_optical_flow_endpoint(client):
    prev, curr = create_test_frame_pair()
    f1_bytes = _encode_frame_as_png(prev)
    f2_bytes = _encode_frame_as_png(curr)

    response = await client.post(
        "/api/vision/optical-flow",
        params={"method": "lucas-kanade"},
        files=[
            ("frame1", ("f1.png", io.BytesIO(f1_bytes), "image/png")),
            ("frame2", ("f2.png", io.BytesIO(f2_bytes), "image/png")),
        ],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "lucas-kanade"
    assert "stats" in data
    assert "visualization" in data
    assert data["processing_time_ms"] >= 0


@pytest.mark.anyio
async def test_api_frame_diff_endpoint(client):
    prev, curr = create_test_frame_pair()
    f1_bytes = _encode_frame_as_png(prev)
    f2_bytes = _encode_frame_as_png(curr)

    response = await client.post(
        "/api/vision/frame-diff",
        params={"method": "consecutive", "threshold": 25},
        files=[
            ("frame1", ("f1.png", io.BytesIO(f1_bytes), "image/png")),
            ("frame2", ("f2.png", io.BytesIO(f2_bytes), "image/png")),
        ],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "consecutive"
    assert data["motion_percentage"] > 0
    assert "motion_mask" in data
    assert "stats" in data
