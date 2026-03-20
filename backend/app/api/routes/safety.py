"""Safety & Privacy API routes — scanning, redaction, watermarking."""

from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.responses import JSONResponse

from app.schemas.safety import (
    ContentSafetyResult,
    RedactRequest,
    RedactionResult,
    ReportRequest,
    SafetyReport,
    SafetyScanResult,
)
from app.services.safety.scanner import SafetyScanner
from app.services.safety.content_safety import ContentSafetyChecker

router = APIRouter(prefix="/api/safety", tags=["safety"])

_scanner = SafetyScanner()
_content_checker = ContentSafetyChecker()

# In-memory scan result store (simple dict keyed by auto-incrementing id)
_scan_store: dict[str, dict] = {}
_scan_counter: int = 0


def _next_scan_id() -> str:
    global _scan_counter
    _scan_counter += 1
    return str(_scan_counter)


def _decode_image(data: bytes) -> np.ndarray:
    """Decode uploaded image bytes into a BGR numpy array."""
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image file")
    return image


def _encode_image_base64(image: np.ndarray) -> str:
    """Encode a BGR numpy array as a base64 PNG string."""
    _, buf = cv2.imencode(".png", image)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


@router.post("/scan", response_model=SafetyScanResult)
async def safety_scan(
    file: UploadFile = File(None),
    scan_type: str = Form("image"),
    text: str = Form(None),
):
    """Scan an uploaded file or text for safety / privacy concerns."""
    if scan_type == "image":
        if file is None:
            raise HTTPException(status_code=400, detail="File required for image scan")
        data = await file.read()
        image = _decode_image(data)
        result = await _scanner.scan_image(image)

    elif scan_type == "text":
        if text is None and file is not None:
            text = (await file.read()).decode("utf-8", errors="replace")
        if not text:
            raise HTTPException(status_code=400, detail="Text required for text scan")
        pii = _scanner.detect_text_pii(text)
        risk = min(len(pii) * 0.15, 1.0)
        recs = []
        if pii:
            recs.append("PII detected — consider redacting before sharing.")
        result = {
            "faces_detected": 0,
            "face_locations": [],
            "pii_found": pii,
            "risk_score": risk,
            "recommendations": recs,
        }

    elif scan_type == "audio":
        if text is None and file is not None:
            text = (await file.read()).decode("utf-8", errors="replace")
        if not text:
            raise HTTPException(status_code=400, detail="Transcript text required for audio scan")
        pii = await _scanner.scan_audio_pii(text)
        risk = min(len(pii) * 0.15, 1.0)
        recs = []
        if pii:
            recs.append("PII detected in audio transcript — consider redacting.")
        result = {
            "faces_detected": 0,
            "face_locations": [],
            "pii_found": pii,
            "risk_score": risk,
            "recommendations": recs,
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scan_type: {scan_type}")

    # Store for later report aggregation
    scan_id = _next_scan_id()
    _scan_store[scan_id] = result

    return result


@router.post("/blur-faces")
async def blur_faces(file: UploadFile = File(...)):
    """Detect and blur faces in an uploaded image, return base64 PNG."""
    data = await file.read()
    image = _decode_image(data)
    blurred = await _scanner.blur_faces(image)
    return {"image": _encode_image_base64(blurred)}


@router.post("/redact", response_model=RedactionResult)
async def redact_pii(body: RedactRequest):
    """Redact PII from the provided text."""
    result = await _scanner.redact_pii(body.text)
    return result


@router.post("/watermark")
async def watermark_image(
    file: UploadFile = File(...),
    text: str = Form("VAF-GENERATED"),
):
    """Add a text watermark to an uploaded image, return base64 PNG."""
    data = await file.read()
    image = _decode_image(data)
    watermarked = await _content_checker.watermark_image(image, text=text)
    return {"image": _encode_image_base64(watermarked)}


@router.post("/report", response_model=SafetyReport)
async def safety_report(body: ReportRequest):
    """Generate an aggregated safety report from previous scan results."""
    results: list[dict] = []
    for sid in body.scan_ids:
        if sid in _scan_store:
            results.append(_scan_store[sid])

    if not results:
        # If no valid IDs, return empty report
        return {
            "total_scans": 0,
            "faces_found": 0,
            "pii_instances": 0,
            "avg_risk_score": 0.0,
            "recommendations": [],
        }

    report = await _scanner.generate_safety_report(results)
    return report
