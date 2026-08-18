"""Vertical Packs routes — industry-specific module packs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.vertical import InstalledVerticalPack, VerticalInstallJob

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

def _scoped(stmt, workspace_id, model):
    """Constrain a query to one workspace when one was supplied."""
    if workspace_id:
        return stmt.where(model.workspace_id == uuid.UUID(str(workspace_id)))
    return stmt.where(model.workspace_id.is_(None))


def _serialise_install(row: InstalledVerticalPack) -> dict[str, Any]:
    """Render an installed pack: stored toggles over the pack's static metadata."""
    pack = VERTICAL_PACKS.get(row.pack_id, {})
    return {
        **pack,
        "pack_id": row.pack_id,
        "installed_version": row.installed_version,
        "enabled": row.enabled,
        "enabled_modules": row.enabled_modules or {},
        "enabled_pipelines": row.enabled_pipelines or {},
        "enabled_alerts": row.enabled_alerts or {},
    }


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

async def _installed_versions(
    db: AsyncSession, workspace_id: str | None
) -> dict[str, str | None]:
    """Map pack_id -> installed_version for one workspace."""
    rows = (
        await db.execute(
            _scoped(select(InstalledVerticalPack), workspace_id, InstalledVerticalPack)
        )
    ).scalars().all()
    return {r.pack_id: r.installed_version for r in rows}


@router.get("/packs")
async def list_packs(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict[str, Any]]:
    """List all built-in vertical packs with full metadata."""
    installed = await _installed_versions(db, workspace_id)

    result = []
    for pack in VERTICAL_PACKS.values():
        entry = dict(pack)
        entry["installed"] = pack["id"] in installed
        if pack["id"] in installed:
            entry["installed_version"] = installed[pack["id"]]
        result.append(entry)
    return result


@router.get("/packs/{pack_id}")
async def get_pack(
    pack_id: str,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get details of a vertical pack."""
    if pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")

    installed = await _installed_versions(db, workspace_id)
    pack = dict(VERTICAL_PACKS[pack_id])
    pack["installed"] = pack_id in installed
    if pack_id in installed:
        pack["installed_version"] = installed[pack_id]
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
async def install_pack(
    body: InstallRequest,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Install a vertical pack. Returns a job_id for status tracking."""
    if body.pack_id not in VERTICAL_PACKS:
        raise HTTPException(status_code=404, detail="Pack not found")

    pack = VERTICAL_PACKS[body.pack_id]
    ws = uuid.UUID(str(workspace_id)) if workspace_id else None

    existing = (
        await db.execute(
            _scoped(
                select(InstalledVerticalPack).where(
                    InstalledVerticalPack.pack_id == body.pack_id
                ),
                workspace_id,
                InstalledVerticalPack,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = InstalledVerticalPack(workspace_id=ws, pack_id=body.pack_id)
        db.add(existing)

    existing.installed_version = pack["version"]
    existing.enabled = True
    existing.enabled_modules = {m: True for m in pack["modules"]}
    existing.enabled_pipelines = {p: True for p in pack["pipelines"]}
    existing.enabled_alerts = {a: True for a in pack["alerts"]}

    # The install itself is synchronous, so the job is recorded as completed
    # rather than reporting fabricated intermediate progress.
    job = VerticalInstallJob(
        workspace_id=ws,
        pack_id=body.pack_id,
        status="completed",
        steps=[
            {"name": "load_pipelines", "status": "completed", "progress": 100},
            {"name": "configure_alerts", "status": "completed", "progress": 100},
            {"name": "verify_install", "status": "completed", "progress": 100},
        ],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # The install has already finished by the time this returns, so report the
    # outcome rather than handing back a job id to poll for a completed job.
    return {
        "job_id": str(job.id),
        "pack_id": body.pack_id,
        "status": "installed",
        "version": pack["version"],
        "modules": list(pack["modules"]),
        "pipelines": list(pack["pipelines"]),
        "alerts": list(pack["alerts"]),
    }


@router.get("/install/{job_id}/status")
async def get_install_status(
    job_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get progress/status of an installation job."""
    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Install job not found")

    job = (
        await db.execute(
            select(VerticalInstallJob).where(VerticalInstallJob.id == jid)
        )
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Install job not found")

    return {
        "job_id": str(job.id),
        "pack_id": job.pack_id,
        "status": job.status,
        "steps": job.steps or [],
    }


@router.get("/installed")
async def list_installed(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict[str, Any]]:
    """List all currently installed vertical packs."""
    rows = (
        await db.execute(
            _scoped(select(InstalledVerticalPack), workspace_id, InstalledVerticalPack)
        )
    ).scalars().all()
    return [_serialise_install(r) for r in rows]


@router.patch("/install/{pack_id}")
async def update_install(
    pack_id: str,
    body: ComponentToggleRequest,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Update component toggles (modules/pipelines/alerts) on an installed pack."""
    row = (
        await db.execute(
            _scoped(
                select(InstalledVerticalPack).where(
                    InstalledVerticalPack.pack_id == pack_id
                ),
                workspace_id,
                InstalledVerticalPack,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Installed pack not found")

    # Reassign rather than mutate: SQLAlchemy does not track in-place edits to
    # a JSON column, so mutating the dict would not be written back.
    for field, updates in (
        ("enabled_modules", body.modules),
        ("enabled_pipelines", body.pipelines),
        ("enabled_alerts", body.alerts),
    ):
        if updates is None:
            continue
        current = dict(getattr(row, field) or {})
        for key, value in updates.items():
            if key in current:
                current[key] = value
        setattr(row, field, current)

    await db.commit()
    await db.refresh(row)
    return {"pack_id": pack_id, "status": "updated", **_serialise_install(row)}


@router.delete("/install/{pack_id}")
async def uninstall_pack(
    pack_id: str,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Uninstall a vertical pack."""
    row = (
        await db.execute(
            _scoped(
                select(InstalledVerticalPack).where(
                    InstalledVerticalPack.pack_id == pack_id
                ),
                workspace_id,
                InstalledVerticalPack,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Installed pack not found")

    await db.delete(row)
    await db.commit()
    return {"pack_id": pack_id, "status": "uninstalled", "success": True}
