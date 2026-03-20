"""Edge Fleet Manager API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.edge.fleet import (
    DeviceRegistry,
    OTAUpdateService,
    RemoteConfigService,
    OfflinePackageBuilder,
    SyncService,
    DeviceHealthService,
)

router = APIRouter(prefix="/api/edge", tags=["edge-fleet"])

# Service singletons
_registry = DeviceRegistry()
_ota = OTAUpdateService()
_config = RemoteConfigService()
_packages = OfflinePackageBuilder()
_sync = SyncService()
_health = DeviceHealthService()

# Placeholder DB
_db: Any = None


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class RegisterDeviceRequest(BaseModel):
    workspace_id: str
    device_name: str
    device_type: str
    hardware_info: dict
    network_info: dict | None = None


class HeartbeatRequest(BaseModel):
    status_payload: dict


class CreateUpdateRequest(BaseModel):
    workspace_id: str
    model_id: str
    target_devices: list[str] | str
    strategy: str = "rolling"


class SetConfigRequest(BaseModel):
    config: dict


class BuildPackageRequest(BaseModel):
    model_id: str
    device_type: str
    include_runtime: bool = True


# ---------------------------------------------------------------------------
# Device Registry Endpoints
# ---------------------------------------------------------------------------

@router.post("/devices")
async def register_device(req: RegisterDeviceRequest):
    try:
        result = await _registry.register_device(
            _db, req.workspace_id, req.device_name, req.device_type,
            req.hardware_info, req.network_info,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/devices")
async def list_devices(workspace_id: str, status: str | None = None):
    return await _registry.list_devices(_db, workspace_id, status)


@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(device_id: str, req: HeartbeatRequest):
    try:
        return await _registry.heartbeat(_db, device_id, req.status_payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/devices/{device_id}")
async def get_device(device_id: str):
    try:
        return await _registry.get_device(_db, device_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/devices/{device_id}")
async def deregister_device(device_id: str):
    result = await _registry.deregister_device(_db, device_id)
    if not result:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"deleted": True}


@router.get("/fleet/overview")
async def fleet_overview(workspace_id: str):
    return await _registry.get_fleet_overview(_db, workspace_id)


# ---------------------------------------------------------------------------
# OTA Update Endpoints
# ---------------------------------------------------------------------------

@router.post("/updates")
async def create_update(req: CreateUpdateRequest):
    try:
        return await _ota.create_update(
            _db, req.workspace_id, req.model_id, req.target_devices, req.strategy,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/updates/{update_id}")
async def get_update_status(update_id: str):
    try:
        return await _ota.get_update_status(_db, update_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/updates/{update_id}/approve")
async def approve_update(update_id: str):
    try:
        return await _ota.approve_update(_db, update_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/updates/{update_id}/rollback")
async def rollback_update(update_id: str):
    try:
        return await _ota.rollback_update(_db, update_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Remote Config Endpoints
# ---------------------------------------------------------------------------

@router.get("/devices/{device_id}/config")
async def get_device_config(device_id: str):
    try:
        return await _config.get_config(_db, device_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/devices/{device_id}/config")
async def set_device_config(device_id: str, req: SetConfigRequest):
    try:
        return await _config.set_config(_db, device_id, req.config)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Offline Package Endpoints
# ---------------------------------------------------------------------------

@router.post("/packages")
async def build_package(req: BuildPackageRequest):
    return await _packages.build_package(
        _db, req.model_id, req.device_type, req.include_runtime,
    )


@router.get("/packages")
async def list_packages(workspace_id: str):
    return await _packages.list_packages(_db, workspace_id)


# ---------------------------------------------------------------------------
# Health Endpoints
# ---------------------------------------------------------------------------

@router.get("/devices/{device_id}/health")
async def device_health(device_id: str):
    try:
        return await _health.get_device_health(_db, device_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/fleet/health")
async def fleet_health(workspace_id: str):
    return await _health.get_fleet_health(_db, workspace_id)
