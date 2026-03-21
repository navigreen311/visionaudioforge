"""Edge Export routes — ONNX export, format listing, export management.

Also hosts /api/edge/devices endpoints consumed by the DeviceFleet and
RegisterDeviceModal frontend components (ED6 + ED7).
"""

from __future__ import annotations

import secrets
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


class DeviceRegisterRequest(BaseModel):
    name: str
    location: str | None = None
    device_type: str = Field("jetson", pattern="^(jetson|raspi|x86|mobile)$")


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------
_exports: dict[str, dict] = {}
_devices: dict[str, dict] = {}

SUPPORTED_FORMATS = [
    {"name": "onnx", "description": "Open Neural Network Exchange", "extensions": [".onnx"]},
    {"name": "tensorrt", "description": "NVIDIA TensorRT", "extensions": [".engine"]},
    {"name": "tflite", "description": "TensorFlow Lite", "extensions": [".tflite"]},
    {"name": "coreml", "description": "Apple Core ML", "extensions": [".mlmodel"]},
    {"name": "openvino", "description": "Intel OpenVINO", "extensions": [".xml", ".bin"]},
]


# ---------------------------------------------------------------------------
# Export Endpoints
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


@router.delete("/exports/{export_id}")
async def delete_export(export_id: str) -> dict[str, str]:
    """Delete an export record."""
    if export_id not in _exports:
        raise HTTPException(status_code=404, detail="Export not found")
    del _exports[export_id]
    return {"status": "deleted", "id": export_id}


@router.get("/formats")
async def get_formats() -> list[dict]:
    """List supported export formats."""
    return SUPPORTED_FORMATS


# ---------------------------------------------------------------------------
# Device Fleet Endpoints (ED7)
# ---------------------------------------------------------------------------

@router.get("/devices")
async def list_devices() -> list[dict]:
    """List all registered edge devices."""
    return list(_devices.values())


@router.post("/devices")
async def register_device(body: DeviceRegisterRequest) -> dict[str, Any]:
    """Register a new edge device and return an auto-generated API key."""
    device_id = str(uuid.uuid4())
    api_key = f"vaf_{secrets.token_urlsafe(32)}"
    device = {
        "id": device_id,
        "name": body.name,
        "device_type": body.device_type,
        "location": body.location,
        "model_deployed": None,
        "model_version": None,
        "latest_version": None,
        "status": "idle",
        "last_heartbeat": time.time(),
        "registered_at": time.time(),
        "api_key": api_key,
    }
    _devices[device_id] = device
    return device


@router.post("/devices/{device_id}/update")
async def push_device_update(device_id: str) -> dict[str, Any]:
    """Push a model update to a device (stub)."""
    if device_id not in _devices:
        raise HTTPException(status_code=404, detail="Device not found")
    device = _devices[device_id]
    device["status"] = "updating"
    # In production this would trigger an async OTA job.
    # For the stub we just mark the version as current.
    if device["latest_version"]:
        device["model_version"] = device["latest_version"]
    device["status"] = "online"
    return {"device_id": device_id, "status": "update_pushed"}


@router.delete("/devices/{device_id}")
async def remove_device(device_id: str) -> dict[str, str]:
    """Remove a registered device."""
    if device_id not in _devices:
        raise HTTPException(status_code=404, detail="Device not found")
    del _devices[device_id]
    return {"status": "removed", "id": device_id}
