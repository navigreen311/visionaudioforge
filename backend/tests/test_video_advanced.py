"""Tests for AdvancedVideoTransform and advanced video API endpoints."""

from __future__ import annotations

import base64

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.transform.video_advanced import AdvancedVideoTransform

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

svc = AdvancedVideoTransform()


def _solid_image(color: tuple[int, ...], h: int = 100, w: int = 100) -> np.ndarray:
    """Create a solid BGR image."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = color
    return img


def _gradient_image(h: int = 100, w: int = 100) -> np.ndarray:
    """Create a BGR image with a horizontal gradient."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        val = int(255 * x / w)
        img[:, x] = (val, val, val)
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


class TestInpaint:
    @pytest.mark.anyio
    async def test_inpaint_fills_mask_area(self):
        # Create image with a black rectangle
        img = _solid_image((200, 200, 200))
        cv2.rectangle(img, (30, 30), (70, 70), (0, 0, 0), -1)

        # Mask covering the black rectangle
        mask = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(mask, (30, 30), (70, 70), 255, -1)

        result = await svc.inpaint(img, mask)
        assert result.shape == img.shape
        # The inpainted area should no longer be pure black
        roi = result[40:60, 40:60]
        mean_val = np.mean(roi)
        assert mean_val > 10, "Inpainted region should not remain black"


class TestFrameInterpolation:
    @pytest.mark.anyio
    async def test_frame_interpolation_creates_intermediate(self):
        frame1 = _solid_image((0, 0, 255), h=50, w=50)    # Red
        frame2 = _solid_image((255, 0, 0), h=50, w=50)    # Blue
        intermediates = await svc.frame_interpolation(frame1, frame2, num_intermediate=3)
        assert len(intermediates) == 3
        for f in intermediates:
            assert f.shape == frame1.shape

    @pytest.mark.anyio
    async def test_frame_interpolation_single(self):
        frame1 = _gradient_image(50, 50)
        frame2 = _gradient_image(50, 50)
        intermediates = await svc.frame_interpolation(frame1, frame2, num_intermediate=1)
        assert len(intermediates) == 1

    @pytest.mark.anyio
    async def test_frame_interpolation_zero(self):
        frame1 = _gradient_image(50, 50)
        frame2 = _gradient_image(50, 50)
        intermediates = await svc.frame_interpolation(frame1, frame2, num_intermediate=0)
        assert len(intermediates) == 0


class TestSmartCrop:
    @pytest.mark.anyio
    async def test_smart_crop_center_of_mass(self):
        img = _gradient_image(200, 200)
        result = await svc.smart_crop(img, target_size=(100, 100), method="center_of_mass")
        assert result.shape[:2] == (100, 100)

    @pytest.mark.anyio
    async def test_smart_crop_face_fallback(self):
        img = _gradient_image(200, 200)
        result = await svc.smart_crop(img, target_size=(100, 100), method="face")
        assert result.shape[:2] == (100, 100)

    @pytest.mark.anyio
    async def test_smart_crop_rule_of_thirds(self):
        img = _gradient_image(200, 200)
        result = await svc.smart_crop(img, target_size=(100, 100), method="rule_of_thirds")
        assert result.shape[:2] == (100, 100)


class TestColorGrade:
    @pytest.mark.anyio
    async def test_color_grade_cinematic(self):
        img = _gradient_image()
        result = await svc.color_grade(img, preset="cinematic")
        assert result.shape == img.shape
        assert result.dtype == np.uint8
        # Should not be identical to input
        assert not np.array_equal(img, result)

    @pytest.mark.anyio
    async def test_color_grade_vintage(self):
        img = _gradient_image()
        result = await svc.color_grade(img, preset="vintage")
        assert result.shape == img.shape

    @pytest.mark.anyio
    async def test_color_grade_high_contrast(self):
        img = _gradient_image()
        result = await svc.color_grade(img, preset="high_contrast")
        assert result.shape == img.shape

    @pytest.mark.anyio
    async def test_color_grade_bw_dramatic(self):
        img = _gradient_image()
        result = await svc.color_grade(img, preset="bw_dramatic")
        assert result.shape == img.shape
        # Should be grayscale (all channels equal)
        b, g, r = cv2.split(result)
        assert np.array_equal(b, g) and np.array_equal(g, r)

    @pytest.mark.anyio
    async def test_color_grade_invalid_preset(self):
        img = _gradient_image()
        with pytest.raises(ValueError, match="Unknown color grade preset"):
            await svc.color_grade(img, preset="nonexistent")


class TestSubtitleBurn:
    @pytest.mark.anyio
    async def test_subtitle_burn_adds_text(self):
        img = _solid_image((128, 128, 128), h=200, w=300)
        result = await svc.subtitle_burn(img, text="Hello World", position="bottom")
        assert result.shape == img.shape
        # The image should be modified (text was drawn)
        assert not np.array_equal(img, result)

    @pytest.mark.anyio
    async def test_subtitle_burn_top(self):
        img = _solid_image((128, 128, 128), h=200, w=300)
        result = await svc.subtitle_burn(img, text="Top Text", position="top")
        assert result.shape == img.shape
        assert not np.array_equal(img, result)

    @pytest.mark.anyio
    async def test_subtitle_burn_center(self):
        img = _solid_image((128, 128, 128), h=200, w=300)
        result = await svc.subtitle_burn(img, text="Center", position="center")
        assert result.shape == img.shape


class TestHighlightClip:
    @pytest.mark.anyio
    async def test_highlight_clip_returns_top_k(self):
        frames = [_solid_image((i, i, i)) for i in range(10)]
        scores = [0.1, 0.9, 0.3, 0.8, 0.2, 0.7, 0.4, 0.6, 0.5, 0.0]
        indices = await svc.create_highlight_clip(frames, scores, top_k=3)
        assert len(indices) == 3
        # Should contain the top-3 scoring indices (1, 3, 5)
        assert 1 in indices
        assert 3 in indices
        assert 5 in indices

    @pytest.mark.anyio
    async def test_highlight_clip_empty_scores(self):
        indices = await svc.create_highlight_clip([], [], top_k=5)
        assert indices == []


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_color_grade(client: AsyncClient):
    img = _gradient_image()
    png = _encode_to_png_bytes(img)

    resp = await client.post(
        "/api/transform/video/color-grade",
        files={"file": ("test.png", png, "image/png")},
        data={"preset": "cinematic"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "image" in body
    assert body["preset"] == "cinematic"
    assert body["processing_time_ms"] >= 0


@pytest.mark.anyio
async def test_api_subtitle(client: AsyncClient):
    img = _solid_image((128, 128, 128), h=200, w=300)
    png = _encode_to_png_bytes(img)

    resp = await client.post(
        "/api/transform/video/subtitle",
        files={"file": ("test.png", png, "image/png")},
        data={"text": "Hello World", "position": "bottom"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "image" in body
    assert body["text"] == "Hello World"
    assert body["position"] == "bottom"


@pytest.mark.anyio
async def test_api_inpaint(client: AsyncClient):
    img = _solid_image((200, 200, 200))
    cv2.rectangle(img, (30, 30), (70, 70), (0, 0, 0), -1)
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.rectangle(mask, (30, 30), (70, 70), 255, -1)

    img_png = _encode_to_png_bytes(img)
    mask_png = _encode_to_png_bytes(mask)

    resp = await client.post(
        "/api/transform/video/inpaint",
        files=[
            ("file", ("test.png", img_png, "image/png")),
            ("mask", ("mask.png", mask_png, "image/png")),
        ],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "image" in body
    assert body["processing_time_ms"] >= 0


@pytest.mark.anyio
async def test_api_interpolate(client: AsyncClient):
    frame1 = _solid_image((0, 0, 255), h=50, w=50)
    frame2 = _solid_image((255, 0, 0), h=50, w=50)
    png1 = _encode_to_png_bytes(frame1)
    png2 = _encode_to_png_bytes(frame2)

    resp = await client.post(
        "/api/transform/video/interpolate",
        files=[
            ("frame1", ("frame1.png", png1, "image/png")),
            ("frame2", ("frame2.png", png2, "image/png")),
        ],
        data={"count": "2"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "frames" in body
    assert body["count"] == 2
    assert len(body["frames"]) == 2
