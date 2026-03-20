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
    model_output: str = Form(default="{}"),
):
    """Upload an image and receive a saliency heatmap (base64-encoded PGM)."""
    contents = await file.read()
    # Decode image bytes to numpy array
    try:
        # Attempt to decode as raw image via numpy; fall back to simple grayscale
        arr = np.frombuffer(contents, dtype=np.uint8)
        # Try to interpret as a square-ish grayscale image
        side = int(np.sqrt(len(arr)))
        if side * side == len(arr):
            image = arr.reshape((side, side))
        else:
            # Treat as 1D and reshape to a reasonable rectangle
            h = max(1, int(np.sqrt(len(arr) / 3)))
            w = max(1, len(arr) // (h * 3))
            needed = h * w * 3
            if needed <= len(arr):
                image = arr[:needed].reshape((h, w, 3))
            else:
                image = arr[: h * h].reshape((h, h)) if h * h <= len(arr) else arr.reshape((1, -1))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode image file.")

    import json

    try:
        output = json.loads(model_output)
    except json.JSONDecodeError:
        output = {}

    heatmap = await _explain.compute_saliency_map(image, output)
    b64 = _explain.heatmap_to_base64(heatmap)

    return {"saliency_map_base64": b64, "shape": list(heatmap.shape)}
