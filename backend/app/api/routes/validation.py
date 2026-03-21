"""Validation & Trust API routes — calibration, drift, uncertainty,
model cards, audit trails, and explainability."""

from __future__ import annotations

import base64
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.deps import get_db
from app.services.validation.service import ValidationService
from app.services.validation.explainability import ExplainabilityService

router = APIRouter(prefix="/api/validate", tags=["validation"])

_svc = ValidationService()
_explain = ExplainabilityService()


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------

class CalibrationRequest(BaseModel):
    predictions: list[float]
    ground_truth: list[int]
    n_bins: int = Field(default=10, ge=2, le=100)


class DriftRequest(BaseModel):
    reference_stats: dict[str, dict]
    current_stats: dict[str, dict]


class UncertaintyRequest(BaseModel):
    predictions: list[list[float]]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/calibration")
async def calibration_analysis(body: CalibrationRequest):
    """Compute calibration bins, ECE, and MCE from predictions vs ground truth."""
    try:
        result = await _svc.calibration_analysis(
            body.predictions, body.ground_truth, body.n_bins
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/drift")
async def drift_detection(body: DriftRequest):
    """Detect data drift between reference and current feature statistics."""
    result = await _svc.drift_detection(body.reference_stats, body.current_stats)
    return result


@router.post("/uncertainty")
async def uncertainty_estimation(body: UncertaintyRequest):
    """Analyse prediction uncertainty via entropy."""
    result = await _svc.uncertainty_estimation(body.predictions)
    return result


@router.get("/model-card/{model_id}")
async def get_model_card(model_id: UUID, db: AsyncSession = Depends(get_db)):
    """Generate a model card for the specified model."""
    card = await _svc.generate_model_card(db, model_id)
    if "error" in card:
        raise HTTPException(status_code=404, detail=card["error"])
    return card


@router.get("/audit/{model_id}")
async def get_audit_trail(model_id: UUID, db: AsyncSession = Depends(get_db)):
    """Return audit trail events for a model."""
    events = await _svc.audit_trail(db, model_id)
    return {"model_id": str(model_id), "events": events}


@router.post("/explain")
async def explain_prediction(
    file: UploadFile = File(...),
    model_id: str = Form(default=""),
    method: str = Form(default="grad-cam"),
    target_class: str = Form(default=""),
):
    """Upload an image and receive an explainability result.

    Returns a heatmap overlay (base64 PNG), top-5 predictions,
    and SHAP feature attribution values.  Currently returns mock
    data — wire to real inference in a future iteration.
    """
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    # --- Generate a deterministic mock heatmap (64x64 red-channel gradient PNG) ---
    width, height = 64, 64
    # Build a simple RGBA gradient as raw bytes for a minimal PNG
    try:
        heatmap_array = np.zeros((height, width, 4), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                intensity = int(255 * ((x + y) / (width + height - 2)))
                heatmap_array[y, x] = [intensity, 0, 255 - intensity, 160]
        # Encode to PNG via a minimal approach
        import io
        import struct
        import zlib

        def _encode_png(rgba: np.ndarray) -> bytes:  # type: ignore[return]
            h, w, _ = rgba.shape
            raw_rows = b""
            for row in range(h):
                raw_rows += b"\x00" + rgba[row].tobytes()
            compressed = zlib.compress(raw_rows)

            def _chunk(chunk_type: bytes, data: bytes) -> bytes:
                c = chunk_type + data
                return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

            sig = b"\x89PNG\r\n\x1a\n"
            ihdr_data = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
            return sig + _chunk(b"IHDR", ihdr_data) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")

        png_bytes = _encode_png(heatmap_array)
        heatmap_b64: str | None = base64.b64encode(png_bytes).decode("ascii")
    except Exception:
        heatmap_b64 = None

    # --- Mock predictions ---
    resolved_target = target_class if target_class else "golden_retriever"
    predictions = [
        {"className": "golden_retriever", "confidence": 0.82},
        {"className": "labrador", "confidence": 0.09},
        {"className": "cocker_spaniel", "confidence": 0.04},
        {"className": "irish_setter", "confidence": 0.03},
        {"className": "beagle", "confidence": 0.02},
    ]

    # --- Mock SHAP values ---
    shap_values = [
        {"feature": "ear_texture", "value": 0.34},
        {"feature": "fur_color", "value": 0.28},
        {"feature": "snout_shape", "value": 0.19},
        {"feature": "eye_shape", "value": 0.11},
        {"feature": "body_proportion", "value": 0.06},
        {"feature": "background_grass", "value": -0.05},
        {"feature": "lighting_angle", "value": -0.12},
        {"feature": "image_noise", "value": -0.08},
    ]

    return JSONResponse(
        content={
            "heatmap_b64": heatmap_b64,
            "predictions": predictions,
            "shap_values": shap_values,
            "method": method,
            "target_class": resolved_target,
        }
    )
