"""Vertical Packs routes — industry-specific module packs."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/verticals", tags=["verticals"])


# ---------------------------------------------------------------------------
# Available vertical packs
# ---------------------------------------------------------------------------

VERTICAL_PACKS = {
    "security": {
        "id": "security",
        "name": "Security & Surveillance",
        "description": "Intrusion detection, perimeter monitoring, anomaly alerts",
        "modules": ["motion-detect", "perimeter-fence", "anomaly-alert", "face-blur", "license-plate"],
        "status": "available",
    },
    "manufacturing": {
        "id": "manufacturing",
        "name": "Manufacturing QA",
        "description": "Defect detection, assembly verification, quality metrics",
        "modules": ["defect-detect", "assembly-check", "measurement", "spc-chart"],
        "status": "available",
    },
    "retail": {
        "id": "retail",
        "name": "Retail Analytics",
        "description": "Foot traffic, heatmaps, shelf monitoring, queue detection",
        "modules": ["people-count", "heatmap", "shelf-scan", "queue-detect"],
        "status": "available",
    },
    "healthcare": {
        "id": "healthcare",
        "name": "Healthcare Imaging",
        "description": "Medical image analysis, DICOM support, annotation tools",
        "modules": ["dicom-viewer", "cell-count", "pathology-assist", "radiology-aid"],
        "status": "available",
    },
    "agriculture": {
        "id": "agriculture",
        "name": "Agriculture & Precision Farming",
        "description": "Crop health, drone imagery, yield estimation",
        "modules": ["crop-health", "ndvi-analysis", "pest-detect", "yield-estimate"],
        "status": "available",
    },
    "logistics": {
        "id": "logistics",
        "name": "Logistics & Warehouse",
        "description": "Package tracking, inventory scanning, route optimization",
        "modules": ["barcode-scan", "package-track", "inventory-count", "route-optimize"],
        "status": "available",
    },
    "media": {
        "id": "media",
        "name": "Media & Entertainment",
        "description": "Content moderation, highlight reel, auto-tagging",
        "modules": ["content-moderate", "highlight-detect", "auto-tag", "thumbnail-gen"],
        "status": "available",
    },
}

_installed: dict[str, dict[str, Any]] = {}

# In-memory install jobs: install_id -> status dict
_install_jobs: dict[str, dict[str, Any]] = {}

INSTALL_STEPS = [
    "downloading",
    "installing_pipelines",
    "configuring_alerts",
    "setting_up",
    "done",
]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InstallRequest(BaseModel):
    pack_id: str


class PatchInstallRequest(BaseModel):
    enabled_modules: list[str]


# ---------------------------------------------------------------------------
# Background install simulation
# ---------------------------------------------------------------------------

async def _simulate_install(install_id: str, pack_id: str) -> None:
    """Walk through install steps with delays to simulate real work."""
    job = _install_jobs[install_id]
    for step in INSTALL_STEPS:
        job["step"] = step
        if step == "done":
            job["status"] = "completed"
            job["progress"] = 100
            _installed[pack_id] = dict(VERTICAL_PACKS[pack_id])
            _installed[pack_id]["enabled_modules"] = list(
                VERTICAL_PACKS[pack_id]["modules"]
            )
            break
        await asyncio.sleep(0.8)
        job["progress"] = min(
            100, job["progress"] + 25
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/packs")
async def list_packs() -> list[dict[str, Any]]:
    """List all available vertical packs."""
    return list(VERTICAL_PACKS.values())


@router.get("/packs/{pack_id}")
async def get_pack(pack_id: str) -> dict[str, Any]:
    """Get details of a vertical pack."""
    if pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")
    pack = dict(VERTICAL_PACKS[pack_id])
    pack["installed"] = pack_id in _installed
    return pack


@router.post("/install")
async def install_pack(body: InstallRequest) -> dict[str, Any]:
    """Start installing a vertical pack. Returns an install_id for polling."""
    if body.pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")

    install_id = uuid.uuid4().hex[:12]
    _install_jobs[install_id] = {
        "install_id": install_id,
        "pack_id": body.pack_id,
        "status": "in_progress",
        "step": "downloading",
        "progress": 0,
    }

    # Fire-and-forget the simulated install
    asyncio.create_task(_simulate_install(install_id, body.pack_id))

    return {
        "install_id": install_id,
        "pack_id": body.pack_id,
        "status": "in_progress",
    }


@router.get("/install/{install_id}/status")
async def get_install_status(install_id: str) -> dict[str, Any]:
    """Poll the status of a running install job."""
    job = _install_jobs.get(install_id)
    if not job:
        raise HTTPException(status_code=404, detail="Install job not found")
    return {
        "install_id": job["install_id"],
        "pack_id": job["pack_id"],
        "status": job["status"],
        "step": job["step"],
        "progress": job["progress"],
    }


@router.get("/installed")
async def list_installed() -> list[dict[str, Any]]:
    """List installed vertical packs."""
    return list(_installed.values())


@router.patch("/install/{pack_id}")
async def update_installed_pack(
    pack_id: str, body: PatchInstallRequest
) -> dict[str, Any]:
    """Update enabled modules for an installed pack."""
    if pack_id not in _installed:
        raise HTTPException(status_code=404, detail="Pack not installed")

    valid_modules = set(VERTICAL_PACKS[pack_id]["modules"])
    for mod in body.enabled_modules:
        if mod not in valid_modules:
            raise HTTPException(
                status_code=400, detail=f"Unknown module: {mod}"
            )

    _installed[pack_id]["enabled_modules"] = body.enabled_modules
    return {
        "pack_id": pack_id,
        "enabled_modules": body.enabled_modules,
        "status": "updated",
    }


@router.delete("/install/{pack_id}")
async def uninstall_pack(pack_id: str) -> dict[str, Any]:
    """Uninstall a vertical pack."""
    if pack_id not in _installed:
        raise HTTPException(status_code=404, detail="Pack not installed")
    del _installed[pack_id]
    return {"pack_id": pack_id, "status": "uninstalled"}


@router.get("/packs/{pack_id}/resources")
async def get_pack_resources(pack_id: str) -> dict[str, Any]:
    """Get resources (models, configs) for a pack."""
    if pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")
    return {
        "pack_id": pack_id,
        "models": [f"{pack_id}-model-v1"],
        "configs": [f"{pack_id}-config-default"],
        "pipelines": [f"{pack_id}-pipeline-main"],
        "total_resources": 3,
    }
