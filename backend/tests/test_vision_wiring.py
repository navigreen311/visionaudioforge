"""Tests for the four wired vision API endpoints: analyze, optical-flow, frame-diff, screen-analyze."""

from __future__ import annotations

import json

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _synthetic_bgr(width: int = 64, height: int = 64, color: tuple = (128, 128, 128)) -> np.ndarray:
    """Create a solid-color BGR image."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = color
    return img


def _png_bytes(image: np.ndarray) -> bytes:
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


def _shifted_frame(base: np.ndarray, dx: int = 10, dy: int = 0) -> np.ndarray:
    """Create a translated copy of *base* to simulate motion."""
    h, w = base.shape[:2]
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(base, M, (w, h))


def _scene_with_rectangle() -> np.ndarray:
    """Create a scene with a white rectangle on a dark background (detectable contour)."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (80, 80), (255, 255, 255), -1)
    return img


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_analyze_endpoint():
    """POST /api/vision/analyze applies preprocessing and returns base64 image."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        img = _synthetic_bgr(32, 32, (100, 150, 200))
        operations = json.dumps([{"op": "resize", "params": {"width": 16, "height": 16, "maintain_aspect": False}}])

        resp = await ac.post(
            "/api/vision/analyze",
            files={"file": ("test.png", _png_bytes(img), "image/png")},
            data={"operations": operations},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "image" in body
    assert body["operations_applied"] == 1
    assert body["result_shape"][0] == 16  # height
    assert body["result_shape"][1] == 16  # width
    assert body["processing_time_ms"] >= 0


@pytest.mark.anyio
async def test_optical_flow_endpoint():
    """POST /api/vision/optical-flow returns flow stats and visualization."""
    # Create two frames with a shifted rectangle to generate trackable features
    base = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.rectangle(base, (10, 10), (30, 30), (255, 255, 255), -1)
    cv2.circle(base, (50, 50), 8, (200, 200, 200), -1)
    frame2 = _shifted_frame(base, dx=5, dy=3)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/vision/optical-flow",
            files=[
                ("frame1", ("f1.png", _png_bytes(base), "image/png")),
                ("frame2", ("f2.png", _png_bytes(frame2), "image/png")),
            ],
            params={"method": "farneback"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "farneback"
    assert "mean_magnitude" in body
    assert "visualization" in body
    assert body["processing_time_ms"] >= 0


@pytest.mark.anyio
async def test_frame_diff_endpoint():
    """POST /api/vision/frame-diff returns motion mask and percentage."""
    base = _scene_with_rectangle()
    moved = _shifted_frame(base, dx=15)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/vision/frame-diff",
            files=[
                ("files", ("f1.png", _png_bytes(base), "image/png")),
                ("files", ("f2.png", _png_bytes(moved), "image/png")),
            ],
            params={"threshold": 25},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "consecutive"
    assert "motion_percentage" in body
    assert "motion_mask" in body
    assert body["num_frames"] == 2
    # There should be some detected motion since we shifted the rectangle
    assert body["motion_percentage"] >= 0


@pytest.mark.anyio
async def test_screen_analyze_endpoint():
    """POST /api/vision/screen-analyze returns brightness, edge_density, etc."""
    # Create a simple "UI" image with some rectangles
    img = np.ones((200, 300, 3), dtype=np.uint8) * 240  # light background
    cv2.rectangle(img, (10, 10), (290, 40), (50, 50, 50), -1)  # nav bar
    cv2.rectangle(img, (50, 80), (150, 110), (100, 100, 255), -1)  # button
    cv2.rectangle(img, (50, 130), (250, 150), (200, 200, 200), -1)  # input

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/vision/screen-analyze",
            files={"file": ("screen.png", _png_bytes(img), "image/png")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "brightness" in body
    assert isinstance(body["brightness"], (int, float))
    assert "edge_density" in body
    assert "ui_elements" in body
    assert isinstance(body["ui_elements"], list)
    assert "layout_type" in body
    assert "dominant_colors" in body
    assert body["processing_time_ms"] >= 0
