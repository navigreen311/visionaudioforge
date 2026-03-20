"""Vertical Packs routes — industry-specific module packs."""

from __future__ import annotations

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

_installed: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InstallRequest(BaseModel):
    pack_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/packs")
async def list_packs() -> list[dict]:
    """List all available vertical packs."""
    return list(VERTICAL_PACKS.values())


@router.get("/packs/{pack_id}")
async def get_pack(pack_id: str) -> dict:
    """Get details of a vertical pack."""
    if pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")
    pack = dict(VERTICAL_PACKS[pack_id])
    pack["installed"] = pack_id in _installed
    return pack


@router.post("/install")
async def install_pack(body: InstallRequest) -> dict[str, Any]:
    """Install a vertical pack."""
    if body.pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")
    _installed[body.pack_id] = VERTICAL_PACKS[body.pack_id]
    return {"pack_id": body.pack_id, "status": "installed", "modules": VERTICAL_PACKS[body.pack_id]["modules"]}


@router.get("/installed")
async def list_installed() -> list[dict]:
    """List installed vertical packs."""
    return list(_installed.values())


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
