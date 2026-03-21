"""Validation & Trust API routes — calibration, drift, uncertainty,
model cards, audit trails, and explainability."""

from __future__ import annotations

import base64
import random
from typing import Optional
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


class DriftFeatureResponse(BaseModel):
    feature: str
    reference_mean: float
    current_mean: float
    drift_score: float
    status: str  # "stable" | "minor" | "major"
    ref_distribution: list[float]
    cur_distribution: list[float]


class DriftAnalysisResponse(BaseModel):
    overall_psi: float
    status: str  # "stable" | "minor" | "major"
    features: list[DriftFeatureResponse]
    method: str
    threshold: float


class UncertaintyRequest(BaseModel):
    predictions: list[list[float]]


# ------------------------------------------------------------------
# Helpers — mock drift data generator
# ------------------------------------------------------------------

def _generate_mock_drift_features(
    feature_names: list[str],
    threshold: float,
) -> list[dict]:
    """Return deterministic-looking mock drift data for each feature."""
    features: list[dict] = []
    rng = random.Random(42)

    for name in feature_names:
        ref_mean = round(rng.uniform(0.2, 0.8), 4)
        shift = round(rng.uniform(-0.15, 0.25), 4)
        cur_mean = round(ref_mean + shift, 4)
        drift_score = round(abs(shift) * rng.uniform(1.5, 4.0), 4)

        if drift_score >= threshold * 2:
            status = "major"
        elif drift_score >= threshold:
            status = "minor"
        else:
            status = "stable"

        ref_dist = [round(rng.gauss(ref_mean, 0.12), 4) for _ in range(50)]
        cur_dist = [round(rng.gauss(cur_mean, 0.14), 4) for _ in range(50)]

        features.append({
            "feature": name,
            "reference_mean": ref_mean,
            "current_mean": cur_mean,
            "drift_score": drift_score,
            "status": status,
            "ref_distribution": ref_dist,
            "cur_distribution": cur_dist,
        })

    return features


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
async def drift_detection(
    reference_file: Optional[UploadFile] = File(None),
    current_file: Optional[UploadFile] = File(None),
    use_prod_data: Optional[str] = Form(None),
    prod_window_days: Optional[str] = Form(None),
    feature_names: Optional[str] = Form(None),
    method: str = Form("psi"),
    threshold: str = Form("0.1"),
):
    """Detect data drift between reference and current feature distributions.

    Accepts CSV file uploads or production-data flag. Returns mock data
    (V2 will integrate real statistical tests).
    """
    thresh = float(threshold)

    if feature_names and feature_names.strip():
        names = [n.strip() for n in feature_names.split(",") if n.strip()]
    else:
        names = [
            "edge_density",
            "color_histogram",
            "brightness",
            "contrast",
            "texture_score",
            "noise_level",
            "sharpness",
        ]

    features = _generate_mock_drift_features(names, thresh)

    overall_psi = round(
        sum(f["drift_score"] for f in features) / max(len(features), 1), 4
    )

    if overall_psi >= thresh * 2:
        overall_status = "major"
    elif overall_psi >= thresh:
        overall_status = "minor"
    else:
        overall_status = "stable"

    return DriftAnalysisResponse(
        overall_psi=overall_psi,
        status=overall_status,
        features=[DriftFeatureResponse(**f) for f in features],
        method=method,
        threshold=thresh,
    )


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
