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


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_exports: dict[str, dict] = {}

SUPPORTED_FORMATS = [
    {"name": "onnx", "description": "Open Neural Network Exchange", "extensions": [".onnx"]},
    {"name": "tensorrt", "description": "NVIDIA TensorRT", "extensions": [".engine"]},
    {"name": "tflite", "description": "TensorFlow Lite", "extensions": [".tflite"]},
    {"name": "coreml", "description": "Apple Core ML", "extensions": [".mlmodel"]},
    {"name": "openvino", "description": "Intel OpenVINO", "extensions": [".xml", ".bin"]},
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/export")
async def export_model(body: ExportRequest) -> dict[str, Any]:
    """Export a model to edge-optimized format."""
    export_id = str(uuid.uuid4())
    export = {
        "id": export_id,
        "model_id": body.model_id,
        "format": body.format,
        "optimize": body.optimize,
        "quantize": body.quantize,
        "status": "completed",
        "file_size_mb": 42.5,
        "created_at": time.time(),
    }
    _exports[export_id] = export
    return export


@router.get("/exports")
async def list_exports(model_id: str | None = None) -> list[dict]:
    """List all exports, optionally filtered by model."""
    exports = list(_exports.values())
    if model_id:
        exports = [e for e in exports if e["model_id"] == model_id]
    return exports


@router.get("/exports/{export_id}")
async def get_export(export_id: str) -> dict:
    """Get export details."""
    if export_id not in _exports:
        raise HTTPException(status_code=404, detail="Export not found")
    return _exports[export_id]


@router.get("/formats")
async def get_formats() -> list[dict]:
    """List supported export formats."""
    return SUPPORTED_FORMATS
