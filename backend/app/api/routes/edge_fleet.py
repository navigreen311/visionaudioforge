"""Edge Fleet Manager routes — device registration, heartbeat, health."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/fleet", tags=["fleet"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DeviceRegister(BaseModel):
    name: str
    device_type: str = "edge-node"
    capabilities: dict[str, Any] = Field(default_factory=dict)
    location: str | None = None


class HeartbeatPayload(BaseModel):
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_percent: float | None = None
    active_models: list[str] = Field(default_factory=list)
    inference_count: int = 0


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_devices: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/devices")
async def register_device(body: DeviceRegister) -> dict[str, Any]:
    """Register an edge device."""
    did = str(uuid.uuid4())
    device = {
        "id": did,
        "name": body.name,
        "device_type": body.device_type,
        "capabilities": body.capabilities,
        "location": body.location,
        "status": "online",
        "last_heartbeat": time.time(),
        "registered_at": time.time(),
    }
    _devices[did] = device
    return device


@router.get("/devices")
async def list_devices() -> list[dict]:
    """List all registered devices."""
    return list(_devices.values())


@router.get("/devices/{device_id}")
async def get_device(device_id: str) -> dict:
    """Get device details."""
    if device_id not in _devices:
        raise HTTPException(status_code=404, detail="Device not found")
    return _devices[device_id]


@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(device_id: str, body: HeartbeatPayload) -> dict[str, Any]:
    """Receive heartbeat from a device."""
    if device_id not in _devices:
        raise HTTPException(status_code=404, detail="Device not found")
    _devices[device_id]["last_heartbeat"] = time.time()
    _devices[device_id]["status"] = "online"
    _devices[device_id]["metrics"] = {
        "cpu_percent": body.cpu_percent,
        "memory_percent": body.memory_percent,
        "gpu_percent": body.gpu_percent,
        "active_models": body.active_models,
        "inference_count": body.inference_count,
    }
    return {"device_id": device_id, "status": "acknowledged"}


@router.get("/health")
async def fleet_health() -> dict[str, Any]:
    """Get fleet-wide health summary."""
    devices = list(_devices.values())
    online = [d for d in devices if d["status"] == "online"]
    return {
        "total_devices": len(devices),
        "online": len(online),
        "offline": len(devices) - len(online),
        "status": "healthy" if len(online) == len(devices) else "degraded",
    }
