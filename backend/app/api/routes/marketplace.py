"""Marketplace Installed-plugins routes — list, configure, uninstall."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
# In-memory store (mirrors existing pattern in plugins.py)
# ---------------------------------------------------------------------------

_installed: dict[str, dict[str, Any]] = {}


def _seed_if_empty() -> None:
    """Populate demo data on first access."""
    if _installed:
        return

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    seeds: list[dict[str, Any]] = [
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

    for s in seeds:
        pid = str(uuid.uuid4())
        _installed[pid] = {
            "id": pid,
            **s,
            "installed_at": now,
            "updated_at": now,
        }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/installed", response_model=InstalledListOut)
async def list_installed() -> InstalledListOut:
    """Return all installed plugins with summary stats."""
    _seed_if_empty()
    plugins = list(_installed.values())
    updates = sum(1 for p in plugins if p["version"] != p["latest_version"])
    used = sum(1 for p in plugins if p["used_in_pipelines"] > 0)
    return InstalledListOut(
        total_installed=len(plugins),
        updates_available=updates,
        used_in_pipelines=used,
        plugins=[InstalledPluginOut(**p) for p in plugins],
    )


@router.patch("/plugins/{plugin_id}/config", response_model=InstalledPluginOut)
async def update_config(plugin_id: str, body: PluginConfig) -> InstalledPluginOut:
    """Update configuration for an installed plugin."""
    _seed_if_empty()
    if plugin_id not in _installed:
        raise HTTPException(status_code=404, detail="Installed plugin not found")
    _installed[plugin_id]["config"] = {
        **_installed[plugin_id]["config"],
        **body.config,
    }
    _installed[plugin_id]["updated_at"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
    )
    return InstalledPluginOut(**_installed[plugin_id])


@router.delete("/plugins/{plugin_id}")
async def uninstall_plugin(plugin_id: str) -> dict[str, str]:
    """Uninstall (remove) a plugin."""
    _seed_if_empty()
    if plugin_id not in _installed:
        raise HTTPException(status_code=404, detail="Installed plugin not found")
    name = _installed[plugin_id]["name"]
    del _installed[plugin_id]
    return {"status": "uninstalled", "plugin": name}
