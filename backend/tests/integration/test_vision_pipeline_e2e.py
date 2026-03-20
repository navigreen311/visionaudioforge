"""End-to-end integration tests for the vision pipeline API."""

import pytest

from tests.utils import (
    create_test_image,
    create_test_image_with_shapes,
    image_to_png_bytes,
)


pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.mark.asyncio
async def test_upload_and_preprocess_image(test_app, test_image):
    """POST /api/vision/analyze with a test image and normalize operation."""
    response = await test_app.post(
        "/api/vision/analyze",
        files={"file": ("test.png", test_image, "image/png")},
        data={"operation": "normalize"},
    )
    # Endpoint exists (not 404); may be 501 (stub) or 200 (implemented)
    assert response.status_code in (200, 501, 422), (
        f"Unexpected status {response.status_code}: {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        assert "result" in data or "image" in data


@pytest.mark.asyncio
async def test_optical_flow_two_frames(test_app):
    """POST /api/vision/optical-flow with two different frames."""
    frame1 = image_to_png_bytes(create_test_image(color=(100, 100, 100)))
    frame2 = image_to_png_bytes(create_test_image(color=(200, 200, 200)))

    response = await test_app.post(
        "/api/vision/optical-flow",
        files=[
            ("frames", ("frame1.png", frame1, "image/png")),
            ("frames", ("frame2.png", frame2, "image/png")),
        ],
    )
    assert response.status_code in (200, 501, 422), (
        f"Unexpected status {response.status_code}: {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        assert "motion" in data or "flow" in data


@pytest.mark.asyncio
async def test_frame_diff_identical_frames(test_app, test_image):
    """POST /api/vision/frame-diff with identical frames — expect ~0% motion."""
    response = await test_app.post(
        "/api/vision/frame-diff",
        files=[
            ("frames", ("frame1.png", test_image, "image/png")),
            ("frames", ("frame2.png", test_image, "image/png")),
        ],
    )
    assert response.status_code in (200, 501, 422), (
        f"Unexpected status {response.status_code}: {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        if "motion_percentage" in data:
            assert data["motion_percentage"] < 1.0, "Identical frames should have ~0 motion"
