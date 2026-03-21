"""Edge Export routes — ONNX export, format listing, export management."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/edge", tags=["edge"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    model_id: str
    format: str = Field("onnx", pattern="^(onnx|tensorrt|tflite|coreml|openvino)$")
    optimize: bool = True
    quantize: bool = False


class MultiFormatExportRequest(BaseModel):
    """Export request supporting multiple formats with per-format options."""
    model_id: str
    formats: list[str] = Field(default_factory=lambda: ["onnx"])
    optimization_level: str = "basic"
    format_options: dict[str, dict[str, Any]] = Field(default_factory=dict)


class FormatEstimate(BaseModel):
    """Estimated metrics for an export format."""
    format: str
    estSizeMb: float
    estLatencyMs: float
    compatibility: str
    compression: str


class ExportFormatStatus(BaseModel):
    """Per-format status within an export job."""
    format: str
    status: str = "pending"
    progress: int = 0
    downloadUrl: str | None = None
    error: str | None = None
    sizeMb: float | None = None


class ExportStatusResponse(BaseModel):
    """Full export job status."""
    jobId: str
    status: str
    formats: list[ExportFormatStatus]


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_exports: dict[str, dict[str, Any]] = {}
_export_jobs: dict[str, dict[str, Any]] = {}

SUPPORTED_FORMATS = [
    {"name": "onnx", "description": "Open Neural Network Exchange", "extensions": [".onnx"]},
    {"name": "tensorrt", "description": "NVIDIA TensorRT", "extensions": [".engine"]},
    {"name": "tflite", "description": "TensorFlow Lite", "extensions": [".tflite"]},
    {"name": "coreml", "description": "Apple Core ML", "extensions": [".mlmodel"]},
    {"name": "openvino", "description": "Intel OpenVINO", "extensions": [".xml", ".bin"]},
    {"name": "webgpu", "description": "WebGPU Shader", "extensions": [".wgsl"]},
]

FORMAT_ESTIMATES: dict[str, FormatEstimate] = {
    "onnx": FormatEstimate(format="ONNX", estSizeMb=42.5, estLatencyMs=12.3, compatibility="Universal", compression="None"),
    "tensorrt": FormatEstimate(format="TensorRT", estSizeMb=28.1, estLatencyMs=3.2, compatibility="NVIDIA GPU", compression="FP16"),
    "coreml": FormatEstimate(format="CoreML", estSizeMb=38.7, estLatencyMs=8.5, compatibility="Apple (iOS/macOS)", compression="None"),
    "tflite": FormatEstimate(format="TFLite", estSizeMb=11.2, estLatencyMs=18.7, compatibility="Mobile / Edge", compression="Quantized"),
    "openvino": FormatEstimate(format="OpenVINO", estSizeMb=40.1, estLatencyMs=6.8, compatibility="Intel CPU/GPU/VPU", compression="FP32"),
    "webgpu": FormatEstimate(format="WebGPU", estSizeMb=44.0, estLatencyMs=15.0, compatibility="Modern Browsers", compression="None"),
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/export")
async def export_model(body: MultiFormatExportRequest) -> dict[str, Any]:
    """Export a model to one or more edge-optimized formats.

    Accepts the new multi-format schema. Creates a job with per-format status
    that can be polled via GET /export/{id}/status.
    """
    export_id = str(uuid.uuid4())
    formats_status = []
    for fmt in body.formats:
        formats_status.append({
            "format": fmt,
            "status": "completed",
            "progress": 100,
            "downloadUrl": f"/api/edge/export/{export_id}/download?format={fmt}",
            "error": None,
            "sizeMb": FORMAT_ESTIMATES.get(fmt, FORMAT_ESTIMATES["onnx"]).estSizeMb,
        })

    job: dict[str, Any] = {
        "id": export_id,
        "model_id": body.model_id,
        "formats": body.formats,
        "optimization_level": body.optimization_level,
        "format_options": body.format_options,
        "status": "completed",
        "formats_status": formats_status,
        "created_at": time.time(),
    }
    _export_jobs[export_id] = job
    return job


@router.get("/export/{export_id}/status")
async def get_export_status(export_id: str) -> dict[str, Any]:
    """Get the status of an export job including per-format progress."""
    if export_id not in _export_jobs:
        raise HTTPException(status_code=404, detail="Export job not found")
    job = _export_jobs[export_id]
    return {
        "jobId": job["id"],
        "status": job["status"],
        "formats": job["formats_status"],
    }


@router.get("/format-estimates")
async def get_format_estimates(
    formats: list[str] = Query(default=[]),
) -> list[dict[str, Any]]:
    """Return estimated size, latency, compatibility, and compression for formats."""
    results: list[dict[str, Any]] = []
    for fmt in formats:
        est = FORMAT_ESTIMATES.get(fmt)
        if est:
            results.append(est.model_dump())
    return results


@router.get("/exports")
async def list_exports(model_id: str | None = None) -> list[dict[str, Any]]:
    """List all exports, optionally filtered by model."""
    exports = list(_exports.values())
    if model_id:
        exports = [e for e in exports if e["model_id"] == model_id]
    return exports


@router.get("/exports/{export_id}")
async def get_export(export_id: str) -> dict[str, Any]:
    """Get export details."""
    if export_id not in _exports:
        raise HTTPException(status_code=404, detail="Export not found")
    return _exports[export_id]


@router.get("/formats")
async def get_formats() -> list[dict[str, Any]]:
    """List supported export formats."""
    return SUPPORTED_FORMATS
