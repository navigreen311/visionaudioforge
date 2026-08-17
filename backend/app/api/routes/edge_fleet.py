"""Edge Fleet Manager routes — device registration, heartbeat, health.

These used to keep their own module-level device dict, separate from the one
``app.services.edge.fleet`` used, so a device registered through the API was
invisible to the fleet services and vice versa. Both now read the same tables.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.edge.fleet.device_registry import DeviceRegistry
from app.services.edge.fleet.health import DeviceHealthService

router = APIRouter(prefix="/api/fleet", tags=["fleet"])

_registry = DeviceRegistry()
_health = DeviceHealthService()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DeviceRegister(BaseModel):
    name: str
    device_type: str = "x86_server"
    capabilities: dict[str, Any] = Field(default_factory=dict)
    location: str | None = None
    network_info: dict[str, Any] = Field(default_factory=dict)


class HeartbeatPayload(BaseModel):
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_percent: float | None = None
    active_models: list[str] = Field(default_factory=list)
    inference_count: int = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/devices", status_code=201)
async def register_device(
    body: DeviceRegister,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Register an edge device."""
    hardware_info = dict(body.capabilities)
    if body.location:
        hardware_info["location"] = body.location

    try:
        registered = await _registry.register_device(
            db,
            str(workspace_id),
            device_name=body.name,
            device_type=body.device_type,
            hardware_info=hardware_info,
            network_info=body.network_info,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return await _registry.get_device(db, registered["device_id"]) | {
        "api_key": registered["api_key"],
    }


@router.get("/devices")
async def list_devices(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    status: str | None = Query(None, description="Filter by device status"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List registered devices in a workspace."""
    return await _registry.list_devices(db, str(workspace_id), status=status)


@router.get("/devices/{device_id}")
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get device details including recent telemetry."""
    try:
        return await _registry.get_device(db, device_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Device not found")


@router.delete("/devices/{device_id}", status_code=204, response_class=Response)
async def deregister_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a device from the registry."""
    if not await _registry.deregister_device(db, device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    return Response(status_code=204)


@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(
    device_id: str,
    body: HeartbeatPayload,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Receive a heartbeat from a device and record its telemetry."""
    # The registry stores canonical *_pct keys; the wire format uses *_percent.
    payload = {
        "cpu_pct": body.cpu_percent,
        "memory_pct": body.memory_percent,
        "gpu_pct": body.gpu_percent,
        "active_models": body.active_models,
        "inference_count_24h": body.inference_count,
    }

    try:
        await _registry.heartbeat(db, device_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"device_id": device_id, "status": "acknowledged"}


@router.get("/health")
async def fleet_health(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get fleet-wide health summary."""
    overview = await _registry.get_fleet_overview(db, str(workspace_id))
    health = await _health.get_fleet_health(db, str(workspace_id))

    total = overview["total_devices"]
    return {
        **overview,
        **health,
        "status": "healthy" if total and overview["online"] == total else "degraded",
    }
