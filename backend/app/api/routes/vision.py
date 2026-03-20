"""Vision API routes: optical flow and frame differencing."""

from __future__ import annotations

import base64
import time

import cv2
import numpy as np
from fastapi import APIRouter, File, Query, UploadFile
from starlette.responses import JSONResponse

from app.schemas.vision import (
    FrameDiffMethod,
    FrameDiffResponse,
    MotionStats,
    OpticalFlowMethod,
    OpticalFlowResponse,
)
from app.services.vision.motion import MotionAnalyzer
from app.services.vision.visualization import (
    create_flow_visualization,
    draw_motion_mask_overlay,
    draw_optical_flow_arrows,
)

router = APIRouter(prefix="/api/vision", tags=["vision"])

analyzer = MotionAnalyzer()


async def _read_upload_as_gray(upload: UploadFile) -> tuple[np.ndarray, np.ndarray]:
    """Read an UploadFile and return (bgr_frame, gray_frame)."""
    data = await upload.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return frame, gray


def _encode_image(image: np.ndarray) -> str:
    """Encode an image array to base64 PNG string."""
    _, buf = cv2.imencode(".png", image)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


# -- Existing stubs (kept) -------------------------------------------------

@router.post("/analyze")
async def analyze():
    return JSONResponse(
        status_code=501,
        content={"status": "not_implemented", "module": "vision"},
    )


@router.post("/screen-analyze")
async def screen_analyze():
    return JSONResponse(
        status_code=501,
        content={"status": "not_implemented", "module": "vision"},
    )


# -- Optical flow -----------------------------------------------------------

@router.post("/optical-flow", response_model=OpticalFlowResponse)
async def optical_flow(
    frame1: UploadFile = File(...),
    frame2: UploadFile = File(...),
    method: OpticalFlowMethod = Query(default=OpticalFlowMethod.LUCAS_KANADE),
):
    """Compute optical flow between two uploaded frames."""
    t0 = time.perf_counter()

    bgr1, gray1 = await _read_upload_as_gray(frame1)
    bgr2, gray2 = await _read_upload_as_gray(frame2)

    if method == OpticalFlowMethod.LUCAS_KANADE:
        result = analyzer.lucas_kanade(gray1, gray2)
        stats = analyzer.compute_motion_stats(result)
        viz = draw_optical_flow_arrows(
            bgr2,
            result["tracked_points"]["old"],
            result["tracked_points"]["new"],
        )
    else:
        result = analyzer.farneback_dense(gray1, gray2)
        stats = analyzer.compute_motion_stats(result)
        viz = create_flow_visualization(result["flow"])

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return OpticalFlowResponse(
        method=method.value,
        stats=MotionStats(**stats),
        visualization=_encode_image(viz),
        processing_time_ms=round(elapsed_ms, 2),
    )


# -- Frame differencing -----------------------------------------------------

@router.post("/frame-diff", response_model=FrameDiffResponse)
async def frame_diff(
    frame1: UploadFile = File(...),
    frame2: UploadFile = File(...),
    frame3: UploadFile | None = File(default=None),
    method: FrameDiffMethod = Query(default=FrameDiffMethod.CONSECUTIVE),
    threshold: int = Query(default=25, ge=0, le=255),
):
    """Compute frame differencing between uploaded frames."""
    t0 = time.perf_counter()

    bgr1, gray1 = await _read_upload_as_gray(frame1)
    _bgr2, gray2 = await _read_upload_as_gray(frame2)

    if method == FrameDiffMethod.THREE_FRAME:
        if frame3 is None:
            return JSONResponse(
                status_code=422,
                content={"detail": "Three-frame method requires frame3 upload."},
            )
        _bgr3, gray3 = await _read_upload_as_gray(frame3)
        result = analyzer.frame_diff_three_frame(gray1, gray2, gray3, threshold=threshold)
    else:
        result = analyzer.frame_diff_consecutive(gray1, gray2, threshold=threshold)

    stats = analyzer.compute_motion_stats(result)
    mask_overlay = draw_motion_mask_overlay(bgr1, result["motion_mask"])

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return FrameDiffResponse(
        method=method.value,
        motion_percentage=round(result["motion_percentage"], 4),
        motion_mask=_encode_image(result["motion_mask"]),
        stats=MotionStats(**stats),
        processing_time_ms=round(elapsed_ms, 2),
    )
