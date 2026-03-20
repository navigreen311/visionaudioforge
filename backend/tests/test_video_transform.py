"""Tests for the Video Transform service and API endpoints."""

from __future__ import annotations

import base64
import io

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.transform.video_transform import VideoTransformService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

svc = VideoTransformService()


def _solid_image(color: tuple[int, ...], h: int = 100, w: int = 100) -> np.ndarray:
    """Create a solid BGR image."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = color
    return img


def _encode_to_png_bytes(image: np.ndarray) -> bytes:
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_background_remove_returns_rgba():
    """Output must be a 4-channel (RGBA/BGRA) image."""
    img = _solid_image((255, 255, 255))
    # Draw a dark rectangle in the centre so threshold can separate fg/bg.
    cv2.rectangle(img, (25, 25), (75, 75), (0, 0, 0), -1)
    result = svc.remove_background(img, method="threshold")
    assert result.shape[2] == 4, "Expected 4-channel RGBA output"


def test_background_remove_grabcut_returns_rgba():
    img = _solid_image((200, 200, 200))
    cv2.rectangle(img, (20, 20), (80, 80), (30, 30, 30), -1)
    result = svc.remove_background(img, method="grabcut")
    assert result.shape[2] == 4


def test_super_resolution_doubles_size():
    img = _solid_image((128, 128, 128), h=100, w=100)
    result = svc.super_resolution(img, scale=2)
    assert result.shape[0] == 200
    assert result.shape[1] == 200


def test_super_resolution_4x():
    img = _solid_image((128, 128, 128), h=50, w=50)
    result = svc.super_resolution(img, scale=4)
    assert result.shape[0] == 200
    assert result.shape[1] == 200


def test_style_sketch():
    img = _solid_image((100, 150, 200))
    result = svc.style_transfer(img, style="sketch")
    assert result.shape[:2] == img.shape[:2]
    # Sketch output is grayscale-like: all channels should be roughly equal.
    b, g, r = cv2.split(result)
    assert np.allclose(b, g, atol=1) and np.allclose(g, r, atol=1)


def test_style_edges():
    img = _solid_image((100, 150, 200))
    result = svc.style_transfer(img, style="edges")
    assert result.shape[:2] == img.shape[:2]


def test_style_cartoon():
    img = _solid_image((100, 150, 200))
    cv2.circle(img, (50, 50), 30, (0, 0, 255), -1)
    result = svc.style_transfer(img, style="cartoon")
    assert result.shape[:2] == img.shape[:2]


def test_auto_crop_16_9():
    # 200x200 image cropped to 16:9 should have correct ratio.
    img = _solid_image((128, 128, 128), h=200, w=200)
    result = svc.auto_crop(img, target_aspect="16:9")
    h, w = result.shape[:2]
    actual_ratio = w / h
    expected_ratio = 16 / 9
    assert abs(actual_ratio - expected_ratio) < 0.05, (
        f"Expected ~{expected_ratio:.2f}, got {actual_ratio:.2f}"
    )


def test_auto_crop_1_1():
    img = _solid_image((128, 128, 128), h=100, w=200)
    result = svc.auto_crop(img, target_aspect="1:1")
    h, w = result.shape[:2]
    assert h == w


def test_generate_thumbnail_middle():
    frames = [_solid_image((i * 25, i * 25, i * 25)) for i in range(10)]
    thumb, idx = svc.generate_thumbnail(frames, method="middle")
    assert idx == 5


def test_generate_thumbnail_brightest():
    frames = [_solid_image((10, 10, 10)) for _ in range(5)]
    # Make frame 3 the brightest.
    frames[3] = _solid_image((255, 255, 255))
    _, idx = svc.generate_thumbnail(frames, method="brightest")
    assert idx == 3


def test_generate_thumbnail_first():
    frames = [_solid_image((i * 50, i * 50, i * 50)) for i in range(5)]
    _, idx = svc.generate_thumbnail(frames, method="first")
    assert idx == 0


def test_scene_detection_finds_cuts():
    """Create frames with an abrupt colour change; scene_detection should flag it."""
    # 5 blue frames, then 5 red frames.
    blue_frames = [_solid_image((255, 0, 0)) for _ in range(5)]
    red_frames = [_solid_image((0, 0, 255)) for _ in range(5)]
    frames = blue_frames + red_frames
    cuts = svc.scene_detection(frames, threshold=20.0)
    assert 5 in cuts, f"Expected cut at frame 5, got {cuts}"


def test_scene_detection_no_cuts_on_identical():
    frames = [_solid_image((128, 128, 128)) for _ in range(10)]
    cuts = svc.scene_detection(frames, threshold=30.0)
    assert cuts == []


def test_stabilize_frames_returns_same_count():
    frames = [_solid_image((128, 128, 128), h=200, w=200) for _ in range(5)]
    result = svc.stabilize_frames(frames)
    assert len(result) == len(frames)


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_background_remove(client: AsyncClient):
    img = _solid_image((200, 200, 200))
    cv2.rectangle(img, (20, 20), (80, 80), (0, 0, 0), -1)
    png = _encode_to_png_bytes(img)

    resp = await client.post(
        "/api/transform/video/background-remove",
        files={"file": ("test.png", png, "image/png")},
        data={"method": "threshold"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "image" in body
    assert body["method"] == "threshold"
    assert body["processing_time_ms"] >= 0


@pytest.mark.anyio
async def test_api_super_resolution(client: AsyncClient):
    img = _solid_image((128, 128, 128), h=50, w=50)
    png = _encode_to_png_bytes(img)

    resp = await client.post(
        "/api/transform/video/super-resolution",
        files={"file": ("test.png", png, "image/png")},
        data={"scale": "2"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["original_size"] == [50, 50]
    assert body["output_size"] == [100, 100]
    assert body["scale"] == 2


@pytest.mark.anyio
async def test_api_style(client: AsyncClient):
    img = _solid_image((100, 150, 200))
    png = _encode_to_png_bytes(img)

    resp = await client.post(
        "/api/transform/video/style",
        files={"file": ("test.png", png, "image/png")},
        data={"style": "sketch"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["style"] == "sketch"


@pytest.mark.anyio
async def test_api_auto_crop(client: AsyncClient):
    img = _solid_image((128, 128, 128), h=200, w=200)
    png = _encode_to_png_bytes(img)

    resp = await client.post(
        "/api/transform/video/auto-crop",
        files={"file": ("test.png", png, "image/png")},
        data={"aspect": "16:9"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["original_size"] == [200, 200]
    # 200 wide, cropped to 16:9 means height gets cropped.
    cw, ch = body["cropped_size"]
    assert abs(cw / ch - 16 / 9) < 0.1


@pytest.mark.anyio
async def test_api_thumbnail(client: AsyncClient):
    frames = [_solid_image((i * 50, i * 50, i * 50)) for i in range(5)]
    files = [
        ("files", (f"frame{i}.png", _encode_to_png_bytes(f), "image/png"))
        for i, f in enumerate(frames)
    ]
    resp = await client.post(
        "/api/transform/video/thumbnail",
        files=files,
        data={"method": "middle"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["frame_index"] == 2
