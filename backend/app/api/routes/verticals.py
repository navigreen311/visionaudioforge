"""Vertical Packs routes — industry-specific module packs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/verticals", tags=["verticals"])


# ---------------------------------------------------------------------------
# Available vertical packs (enriched with category/pipelines/alerts/version)
# ---------------------------------------------------------------------------

VERTICAL_PACKS: dict[str, dict[str, Any]] = {
    "security": {
        "id": "security",
        "name": "Security & Surveillance",
        "category": "safety",
        "description": "Intrusion detection, perimeter monitoring, anomaly alerts",
        "modules": ["motion-detect", "perimeter-fence", "anomaly-alert", "face-blur", "license-plate"],
        "pipelines": ["intrusion-detection", "perimeter-monitor", "anomaly-scoring"],
        "alerts": ["zone-breach", "loitering", "tailgating", "camera-tamper"],
        "version": "2.1.0",
        "latest_version": "2.1.0",
        "installed_version": None,
        "status": "available",
    },
    "manufacturing": {
        "id": "manufacturing",
        "name": "Manufacturing QA",
        "category": "industrial",
        "description": "Defect detection, assembly verification, quality metrics",
        "modules": ["defect-detect", "assembly-check", "measurement", "spc-chart"],
        "pipelines": ["defect-inspection", "assembly-verify", "spc-reporting"],
        "alerts": ["defect-rate-high", "assembly-mismatch", "measurement-drift"],
        "version": "1.4.0",
        "latest_version": "1.4.0",
        "installed_version": None,
        "status": "available",
    },
    "retail": {
        "id": "retail",
        "name": "Retail Analytics",
        "category": "commerce",
        "description": "Foot traffic, heatmaps, shelf monitoring, queue detection",
        "modules": ["people-count", "heatmap", "shelf-scan", "queue-detect"],
        "pipelines": ["traffic-analysis", "shelf-compliance", "queue-management"],
        "alerts": ["queue-length-exceeded", "shelf-empty", "occupancy-limit"],
        "version": "1.8.0",
        "latest_version": "1.8.0",
        "installed_version": None,
        "status": "available",
    },
    "healthcare": {
        "id": "healthcare",
        "name": "Healthcare Imaging",
        "category": "medical",
        "description": "Medical image analysis, DICOM support, annotation tools",
        "modules": ["dicom-viewer", "cell-count", "pathology-assist", "radiology-aid"],
        "pipelines": ["dicom-ingest", "pathology-screen", "radiology-triage"],
        "alerts": ["critical-finding", "quality-below-threshold", "calibration-needed"],
        "version": "1.2.0",
        "latest_version": "1.2.0",
        "installed_version": None,
        "status": "available",
    },
    "agriculture": {
        "id": "agriculture",
        "name": "Agriculture & Precision Farming",
        "category": "agritech",
        "description": "Crop health, drone imagery, yield estimation",
        "modules": ["crop-health", "ndvi-analysis", "pest-detect", "yield-estimate"],
        "pipelines": ["drone-survey", "crop-monitor", "yield-forecast"],
        "alerts": ["pest-outbreak", "irrigation-needed", "frost-warning"],
        "version": "1.1.0",
        "latest_version": "1.1.0",
        "installed_version": None,
        "status": "available",
    },
    "logistics": {
        "id": "logistics",
        "name": "Logistics & Warehouse",
        "category": "supply-chain",
        "description": "Package tracking, inventory scanning, route optimization",
        "modules": ["barcode-scan", "package-track", "inventory-count", "route-optimize"],
        "pipelines": ["package-ingest", "inventory-audit", "route-plan"],
        "alerts": ["package-lost", "inventory-mismatch", "delivery-delay"],
        "version": "1.6.0",
        "latest_version": "1.6.0",
        "installed_version": None,
        "status": "available",
    },
    "media": {
        "id": "media",
        "name": "Media & Entertainment",
        "category": "creative",
        "description": "Content moderation, highlight reel, auto-tagging",
        "modules": ["content-moderate", "highlight-detect", "auto-tag", "thumbnail-gen"],
        "pipelines": ["content-review", "highlight-extraction", "auto-tagging"],
        "alerts": ["nsfw-detected", "copyright-match", "quality-degraded"],
        "version": "1.3.0",
        "latest_version": "1.3.0",
        "installed_version": None,
        "status": "available",
    },
}

# In-memory stores
_installed: dict[str, dict[str, Any]] = {}
_install_jobs: dict[str, dict[str, Any]] = {}
_job_counter = 0


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InstallRequest(BaseModel):
    pack_id: str


class ComponentToggleRequest(BaseModel):
    modules: dict[str, bool] | None = None
    pipelines: dict[str, bool] | None = None
    alerts: dict[str, bool] | None = None


# ---------------------------------------------------------------------------
# Endpoints — Browsing packs
# ---------------------------------------------------------------------------

@router.get("/packs")
async def list_packs() -> list[dict[str, Any]]:
    """List all 7 built-in vertical packs with full metadata."""
    result = []
    for pack in VERTICAL_PACKS.values():
        entry = dict(pack)
        # If installed, reflect installed_version
        if pack["id"] in _installed:
            entry["installed_version"] = _installed[pack["id"]].get("installed_version")
        result.append(entry)
    return result


@router.get("/packs/{pack_id}")
async def get_pack(pack_id: str) -> dict[str, Any]:
    """Get details of a vertical pack."""
    if pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")
    pack = dict(VERTICAL_PACKS[pack_id])
    pack["installed"] = pack_id in _installed
    if pack_id in _installed:
        pack["installed_version"] = _installed[pack_id].get("installed_version")
    return pack


@router.get("/packs/{pack_id}/resources")
async def get_pack_resources(pack_id: str) -> dict[str, Any]:
    """Get resources (models, configs) for a pack."""
    if pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")
    pack = VERTICAL_PACKS[pack_id]
    return {
        "pack_id": pack_id,
        "models": [f"{pack_id}-model-v1"],
        "configs": [f"{pack_id}-config-default"],
        "pipelines": [f"{pack_id}-pipeline-main"],
        "total_resources": 3,
    }


# ---------------------------------------------------------------------------
# Endpoints — Install / Uninstall workflow
# ---------------------------------------------------------------------------

@router.post("/install")
async def install_pack(body: InstallRequest) -> dict[str, Any]:
    """Start installing a vertical pack. Returns a job_id for status tracking."""
    global _job_counter

    if body.pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")

    _job_counter += 1
    job_id = f"install_{_job_counter:03d}"

    pack = VERTICAL_PACKS[body.pack_id]

    # Create job with progress steps
    _install_jobs[job_id] = {
        "job_id": job_id,
        "pack_id": body.pack_id,
        "status": "completed",
        "steps": [
            {"name": "download_models", "status": "completed", "progress": 100},
            {"name": "load_pipelines", "status": "completed", "progress": 100},
            {"name": "configure_alerts", "status": "completed", "progress": 100},
            {"name": "verify_install", "status": "completed", "progress": 100},
        ],
    }

    # Mark as installed immediately (stub behaviour)
    _installed[body.pack_id] = {
        **pack,
        "installed_version": pack["version"],
        "enabled_modules": {m: True for m in pack["modules"]},
        "enabled_pipelines": {p: True for p in pack["pipelines"]},
        "enabled_alerts": {a: True for a in pack["alerts"]},
    }

    return {"job_id": job_id}


@router.get("/install/{job_id}/status")
async def get_install_status(job_id: str) -> dict[str, Any]:
    """Get progress/status of an installation job."""
    if job_id not in _install_jobs:
        raise HTTPException(status_code=404, detail="Install job not found")
    return _install_jobs[job_id]


@router.get("/installed")
async def list_installed() -> list[dict[str, Any]]:
    """List all currently installed vertical packs."""
    return list(_installed.values())


@router.patch("/install/{pack_id}")
async def update_install(pack_id: str, body: ComponentToggleRequest) -> dict[str, Any]:
    """Update component toggles (modules/pipelines/alerts) on an installed pack."""
    if pack_id not in _installed:
        raise HTTPException(status_code=404, detail="Installed pack not found")

    entry = _installed[pack_id]

    if body.modules is not None:
        for key, enabled in body.modules.items():
            if key in entry.get("enabled_modules", {}):
                entry["enabled_modules"][key] = enabled

    if body.pipelines is not None:
        for key, enabled in body.pipelines.items():
            if key in entry.get("enabled_pipelines", {}):
                entry["enabled_pipelines"][key] = enabled

    if body.alerts is not None:
        for key, enabled in body.alerts.items():
            if key in entry.get("enabled_alerts", {}):
                entry["enabled_alerts"][key] = enabled

    return {"pack_id": pack_id, "status": "updated", **entry}


@router.delete("/install/{pack_id}")
async def uninstall_pack(pack_id: str) -> dict[str, Any]:
    """Uninstall a vertical pack."""
    if pack_id not in _installed:
        raise HTTPException(status_code=404, detail="Installed pack not found")

    del _installed[pack_id]
    return {"pack_id": pack_id, "status": "uninstalled", "success": True}
