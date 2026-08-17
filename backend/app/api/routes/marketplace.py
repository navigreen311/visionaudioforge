"""Marketplace Installed-plugins routes — list, configure, uninstall."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.plugin import InstalledPlugin

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PluginConfig(BaseModel):
    """Key-value configuration payload."""

    config: dict[str, str | int | float | bool] = Field(default_factory=dict)


class InstalledPluginOut(BaseModel):
    """Shape returned by the installed-plugins endpoint."""

    id: str
    name: str
    version: str
    latest_version: str
    category: str
    description: str
    author: str
    status: str  # "active" | "inactive" | "error"
    used_in_pipelines: int
    config: dict[str, str | int | float | bool]
    installed_at: str
    updated_at: str


class InstalledListOut(BaseModel):
    """Wrapper that includes summary stats."""

    total_installed: int
    updates_available: int
    used_in_pipelines: int
    plugins: list[InstalledPluginOut]


# ---------------------------------------------------------------------------
# Storage
#
# Installed plugins live in the installed_plugins table. Held in a module dict
# they vanished on restart, so the console reported plugins as uninstalled
# that were still wired into pipelines.
# ---------------------------------------------------------------------------

SEED_PLUGINS: list[dict[str, Any]] = [
    {
        "name": "YOLO Detector",
        "version": "1.2.0",
        "latest_version": "1.3.0",
        "category": "vision",
        "description": "Object detection with YOLOv8",
        "author": "VAF Team",
        "status": "active",
        "used_in_pipelines": 3,
        "config": {"confidence_threshold": 0.65, "nms_iou": 0.45},
    },
    {
        "name": "Whisper Transcriber",
        "version": "2.0.0",
        "latest_version": "2.0.0",
        "category": "audio",
        "description": "Speech-to-text with Whisper",
        "author": "VAF Team",
        "status": "active",
        "used_in_pipelines": 2,
        "config": {"language": "en", "beam_size": 5},
    },
    {
        "name": "Slack Notifier",
        "version": "1.0.0",
        "latest_version": "1.0.0",
        "category": "integration",
        "description": "Send alerts to Slack",
        "author": "VAF Team",
        "status": "inactive",
        "used_in_pipelines": 0,
        "config": {"webhook_url": "", "channel": "#alerts"},
    },
]


def _plugin_out(plugin: InstalledPlugin) -> InstalledPluginOut:
    return InstalledPluginOut(
        id=str(plugin.id),
        name=plugin.name,
        version=plugin.version,
        latest_version=plugin.latest_version,
        category=plugin.category,
        description=plugin.description,
        author=plugin.author,
        status=plugin.status,
        used_in_pipelines=plugin.used_in_pipelines,
        config=plugin.config or {},
        installed_at=plugin.created_at.isoformat() if plugin.created_at else "",
        updated_at=plugin.updated_at.isoformat() if plugin.updated_at else "",
    )


async def _seed_if_empty(db: AsyncSession, workspace_id: uuid.UUID | None) -> None:
    """Populate demo plugins the first time a workspace is looked at."""
    query = select(func.count()).select_from(InstalledPlugin)
    if workspace_id is not None:
        query = query.where(InstalledPlugin.workspace_id == workspace_id)

    if (await db.execute(query)).scalar():
        return

    for seed in SEED_PLUGINS:
        db.add(InstalledPlugin(id=uuid.uuid4(), workspace_id=workspace_id, **seed))
    await db.commit()


async def _load(db: AsyncSession, plugin_id: str) -> InstalledPlugin:
    try:
        key = uuid.UUID(plugin_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail="Installed plugin not found")

    result = await db.execute(
        select(InstalledPlugin).where(InstalledPlugin.id == key)
    )
    plugin = result.scalar_one_or_none()
    if plugin is None:
        raise HTTPException(status_code=404, detail="Installed plugin not found")
    return plugin


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/installed", response_model=InstalledListOut)
async def list_installed(
    workspace_id: uuid.UUID | None = Query(None, description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> InstalledListOut:
    """Return all installed plugins with summary stats."""
    await _seed_if_empty(db, workspace_id)

    query = select(InstalledPlugin)
    if workspace_id is not None:
        query = query.where(InstalledPlugin.workspace_id == workspace_id)

    result = await db.execute(query.order_by(InstalledPlugin.created_at))
    plugins = list(result.scalars().all())

    return InstalledListOut(
        total_installed=len(plugins),
        updates_available=sum(1 for p in plugins if p.version != p.latest_version),
        used_in_pipelines=sum(1 for p in plugins if p.used_in_pipelines > 0),
        plugins=[_plugin_out(p) for p in plugins],
    )


@router.patch("/plugins/{plugin_id}/config", response_model=InstalledPluginOut)
async def update_config(
    plugin_id: str,
    body: PluginConfig,
    db: AsyncSession = Depends(get_db),
) -> InstalledPluginOut:
    """Update configuration for an installed plugin."""
    plugin = await _load(db, plugin_id)
    plugin.config = {**(plugin.config or {}), **body.config}
    await db.commit()
    await db.refresh(plugin)
    return _plugin_out(plugin)


@router.delete("/plugins/{plugin_id}")
async def uninstall_plugin(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Uninstall (remove) a plugin."""
    plugin = await _load(db, plugin_id)
    name = plugin.name

    await db.delete(plugin)
    await db.commit()
    return {"status": "uninstalled", "plugin": name}


# ---------------------------------------------------------------------------
# Install / update job tracking
#
# InstallModal POSTs to /install (or /update), then polls /install/status every
# 800ms until status is "completed" or "failed", advancing a step indicator.
# ---------------------------------------------------------------------------

INSTALL_STEPS = ["downloading", "verifying", "installing", "configuring"]

# plugin_id -> job state. Ephemeral by design: an install job that outlives a
# restart has nothing to resume.
_install_jobs: dict[str, dict[str, Any]] = {}


class InstallStartedOut(BaseModel):
    install_id: str


class InstallStatusOut(BaseModel):
    install_id: str
    status: str  # "running" | "completed" | "failed"
    step: str
    error: str | None = None


def _start_job(plugin_id: str, kind: str) -> InstallStartedOut:
    install_id = str(uuid.uuid4())
    _install_jobs[plugin_id] = {
        "install_id": install_id,
        "kind": kind,
        "polls": 0,
        "error": None,
    }
    return InstallStartedOut(install_id=install_id)


@router.post("/plugins/{plugin_id}/install", response_model=InstallStartedOut)
async def install_plugin(plugin_id: str) -> InstallStartedOut:
    """Begin installing a plugin; returns the id to poll for progress."""
    return _start_job(plugin_id, "install")


@router.post("/plugins/{plugin_id}/update", response_model=InstallStartedOut)
async def update_plugin(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
) -> InstallStartedOut:
    """Begin updating an installed plugin to its latest version."""
    await _load(db, plugin_id)
    return _start_job(plugin_id, "update")


@router.get("/plugins/{plugin_id}/install/status", response_model=InstallStatusOut)
async def install_status(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
) -> InstallStatusOut:
    """Advance and report install progress. Each poll moves one step forward."""
    job = _install_jobs.get(plugin_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No install in progress")

    job["polls"] += 1
    idx = job["polls"] - 1

    if idx >= len(INSTALL_STEPS):
        # Job finished: apply the effect to the stored plugin, then report done.
        if job["kind"] == "update":
            plugin = await _load(db, plugin_id)
            plugin.version = plugin.latest_version
            plugin.updated_at = datetime.now(timezone.utc)
            await db.commit()

        return InstallStatusOut(
            install_id=job["install_id"],
            status="completed",
            step=INSTALL_STEPS[-1],
        )

    return InstallStatusOut(
        install_id=job["install_id"],
        status="running",
        step=INSTALL_STEPS[idx],
    )
