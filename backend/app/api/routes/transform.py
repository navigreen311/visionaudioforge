"""Video / Vision Transform API routes.

All endpoints accept uploaded images (PNG / JPEG) and return base64-encoded
PNG results along with metadata.
"""

from __future__ import annotations

import base64
import io
import time

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, UploadFile
from starlette.responses import JSONResponse

from app.services.transform.video_transform import VideoTransformService

router = APIRouter(prefix="/api/transform", tags=["transform"])

_svc = VideoTransformService()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _read_image(upload: UploadFile) -> np.ndarray:
    """Decode an uploaded file into a BGR numpy array."""
    data = await upload.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img


def _encode_png(image: np.ndarray) -> str:
    """Encode a numpy image to a base64 PNG string."""
    _, buf = cv2.imencode(".png", image)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


# ------------------------------------------------------------------
# POST /api/transform/video/background-remove
# ------------------------------------------------------------------

@router.post("/video/background-remove")
async def background_remove(
    file: UploadFile = File(...),
    method: str = Form("threshold"),
):
    start = time.perf_counter()
    image = await _read_image(file)
    result = _svc.remove_background(image, method=method)
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "image": _encode_png(result),
        "method": method,
        "processing_time_ms": round(elapsed, 2),
    }


# ------------------------------------------------------------------
# POST /api/transform/video/super-resolution
# ------------------------------------------------------------------

@router.post("/video/super-resolution")
async def super_resolution(
    file: UploadFile = File(...),
    scale: int = Form(2),
):
    start = time.perf_counter()
    image = await _read_image(file)
    h, w = image.shape[:2]
    result = _svc.super_resolution(image, scale=scale)
    rh, rw = result.shape[:2]
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "image": _encode_png(result),
        "original_size": [w, h],
        "output_size": [rw, rh],
        "scale": scale,
        "processing_time_ms": round(elapsed, 2),
    }


# ------------------------------------------------------------------
# POST /api/transform/video/style
# ------------------------------------------------------------------

@router.post("/video/style")
async def style_transfer(
    file: UploadFile = File(...),
    style: str = Form("sketch"),
):
    start = time.perf_counter()
    image = await _read_image(file)
    result = _svc.style_transfer(image, style=style)
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "image": _encode_png(result),
        "style": style,
        "processing_time_ms": round(elapsed, 2),
    }


# ------------------------------------------------------------------
# POST /api/transform/video/auto-crop
# ------------------------------------------------------------------

@router.post("/video/auto-crop")
async def auto_crop(
    file: UploadFile = File(...),
    aspect: str = Form("16:9"),
):
    image = await _read_image(file)
    h, w = image.shape[:2]
    result = _svc.auto_crop(image, target_aspect=aspect)
    rh, rw = result.shape[:2]
    return {
        "image": _encode_png(result),
        "original_size": [w, h],
        "cropped_size": [rw, rh],
    }


# ------------------------------------------------------------------
# POST /api/transform/video/thumbnail
# ------------------------------------------------------------------

@router.post("/video/thumbnail")
async def thumbnail(
    files: list[UploadFile] = File(...),
    method: str = Form("middle"),
):
    frames: list[np.ndarray] = []
    for f in files:
        frames.append(await _read_image(f))

    thumb, idx = _svc.generate_thumbnail(frames, method=method)
    return {
        "thumbnail": _encode_png(thumb),
        "frame_index": idx,
    }
