"""Vision preprocessing API routes."""

from __future__ import annotations

import json
import time

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, UploadFile
from starlette.responses import JSONResponse

from app.schemas.vision import ScreenAnalyzeResponse, VisionAnalyzeResponse
from app.services.vision.preprocessing import ImagePreprocessor
from app.services.vision.utils import (
    calculate_image_stats,
    image_to_base64,
    validate_image,
)

router = APIRouter(prefix="/api/vision", tags=["vision"])

_preprocessor = ImagePreprocessor()


@router.post("/analyze", response_model=VisionAnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    operations: str = Form("[]"),
):
    """Apply a sequence of preprocessing operations to an uploaded image.

    ``operations`` is a JSON string, e.g.
    ``[{"op": "normalize", "params": {"method": "min_max"}}]``
    """
    start = time.perf_counter()

    # Read & validate
    file_bytes = await file.read()
    try:
        image = validate_image(file_bytes)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # Parse operations
    try:
        ops = json.loads(operations)
    except json.JSONDecodeError as exc:
        return JSONResponse(status_code=400, content={"detail": f"Invalid JSON: {exc}"})

    # Apply pipeline
    try:
        result = _preprocessor.preprocess_pipeline(image, ops)
    except (ValueError, KeyError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    elapsed_ms = (time.perf_counter() - start) * 1000

    # If the result is float, scale to uint8 for encoding
    if result.dtype in (np.float32, np.float64):
        r_min, r_max = float(result.min()), float(result.max())
        if r_min == r_max:
            encode_img = np.zeros_like(result, dtype=np.uint8)
        else:
            encode_img = ((result - r_min) / (r_max - r_min) * 255).astype(np.uint8)
    else:
        encode_img = result

    return VisionAnalyzeResponse(
        image=image_to_base64(encode_img),
        stats=calculate_image_stats(result),
        operations_applied=[op.get("op", "") if isinstance(op, dict) else op for op in ops],
        processing_time_ms=round(elapsed_ms, 2),
    )


@router.post("/screen-analyze", response_model=ScreenAnalyzeResponse)
async def screen_analyze(file: UploadFile = File(...)):
    """Analyze visual properties of a screenshot (no OCR)."""
    file_bytes = await file.read()
    try:
        image = validate_image(file_bytes)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    h, w = image.shape[:2]

    # Brightness: mean of grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())

    # Edge density: fraction of edge pixels
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / (h * w)

    # Dominant colors via k-means (k=5)
    pixels = image.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, _, centers = cv2.kmeans(pixels, 5, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    dominant_colors = centers.astype(int).tolist()

    return ScreenAnalyzeResponse(
        brightness=round(brightness, 2),
        edge_density=round(edge_density, 4),
        dominant_colors=dominant_colors,
        resolution=[w, h],
    )


@router.post("/optical-flow")
async def optical_flow():
    return JSONResponse(
        status_code=501,
        content={"status": "not_implemented", "module": "vision"},
    )


@router.post("/frame-diff")
async def frame_diff():
    return JSONResponse(
        status_code=501,
        content={"status": "not_implemented", "module": "vision"},
    )
