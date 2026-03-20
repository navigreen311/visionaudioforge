"""Vision API routes: detection, OCR, error analysis, and stubs."""

from __future__ import annotations

import base64
import time

import cv2
import numpy as np
from fastapi import APIRouter, File, Query, UploadFile
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.services.vision.detection import ObjectDetector
from app.services.vision.error_analysis import generate_quality_report
from app.services.vision.ocr import OCREngine

router = APIRouter(prefix="/api/vision", tags=["vision"])

# Shared service singletons (lazy-loaded internally)
_detector = ObjectDetector()
_ocr_engine = OCREngine()


# ------------------------------------------------------------------
# Existing stub endpoints (preserved)
# ------------------------------------------------------------------


@router.post("/analyze")
async def analyze():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


@router.post("/optical-flow")
async def optical_flow():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


@router.post("/frame-diff")
async def frame_diff():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


@router.post("/screen-analyze")
async def screen_analyze():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


# ------------------------------------------------------------------
# Object detection
# ------------------------------------------------------------------


@router.post("/detect")
async def detect(
    file: UploadFile = File(...),
    confidence: float = Query(0.5, ge=0.0, le=1.0),
    classes: str | None = Query(None, description="Comma-separated class IDs"),
):
    """Detect objects in an uploaded image."""
    t0 = time.perf_counter()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    class_ids = None
    if classes:
        class_ids = [int(c.strip()) for c in classes.split(",") if c.strip().isdigit()]

    detections = _detector.detect(image, confidence=confidence, classes=class_ids or None)

    # Generate annotated visualization
    annotated = _detector.draw_detections(image, detections)
    _, buf = cv2.imencode(".png", annotated)
    visualization = base64.b64encode(buf.tobytes()).decode("utf-8")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "detections": detections,
        "count": len(detections),
        "visualization": visualization,
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# OCR
# ------------------------------------------------------------------


@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    """Extract text from an uploaded image using OCR."""
    t0 = time.perf_counter()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    result = _ocr_engine.extract_text(image)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "full_text": result["full_text"],
        "blocks": result.get("blocks", []),
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# Error analysis
# ------------------------------------------------------------------


class ErrorAnalysisRequest(BaseModel):
    predictions: list[str]
    ground_truth: list[str]
    classes: list[str]


@router.post("/error-analysis")
async def error_analysis(body: ErrorAnalysisRequest):
    """Compute classification error analysis from predictions vs ground truth."""
    if len(body.predictions) != len(body.ground_truth):
        return JSONResponse(
            status_code=400,
            content={"error": "predictions and ground_truth must have the same length"},
        )

    report = generate_quality_report(body.ground_truth, body.predictions, body.classes)
    return report
