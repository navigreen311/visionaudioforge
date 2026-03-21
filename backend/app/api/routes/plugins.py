"""Plugin Marketplace routes — registration, enable/disable, execution."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PluginRegister(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    entry_point: str = ""
    capabilities: list[str] = Field(default_factory=list)


class PluginExecute(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_plugins: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register")
async def register_plugin(body: PluginRegister) -> dict[str, Any]:
    """Register a new plugin."""
    pid = str(uuid.uuid4())
    plugin = {
        "id": pid,
        "name": body.name,
        "version": body.version,
        "description": body.description,
        "author": body.author,
        "entry_point": body.entry_point,
        "capabilities": body.capabilities,
        "enabled": False,
        "installed_at": time.time(),
    }
    _plugins[pid] = plugin
    return plugin


@router.get("/")
async def list_plugins() -> list[dict]:
    """List all registered plugins."""
    return list(_plugins.values())


@router.get("/{plugin_id}")
async def get_plugin(plugin_id: str) -> dict:
    """Get plugin details."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return _plugins[plugin_id]


@router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str) -> dict[str, Any]:
    """Enable a plugin."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    _plugins[plugin_id]["enabled"] = True
    return {"plugin_id": plugin_id, "enabled": True}


@router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str) -> dict[str, Any]:
    """Disable a plugin."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    _plugins[plugin_id]["enabled"] = False
    return {"plugin_id": plugin_id, "enabled": False}


@router.post("/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, body: PluginExecute) -> dict[str, Any]:
    """Execute a plugin action."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    if not _plugins[plugin_id]["enabled"]:
        raise HTTPException(status_code=400, detail="Plugin is not enabled")
    return {
        "plugin_id": plugin_id,
        "action": body.action,
        "status": "executed",
        "result": {"message": f"Action '{body.action}' executed successfully"},
    }


@router.get("/marketplace/featured")
async def marketplace_featured() -> list[dict]:
    """Get featured plugins from the marketplace."""
    return [
        {"name": "Auto-Label", "description": "Automatic image labeling", "downloads": 1520},
        {"name": "Video Summarizer", "description": "AI video summarization", "downloads": 980},
        {"name": "Data Augmentor", "description": "Smart data augmentation", "downloads": 2100},
    ]


# ---------------------------------------------------------------------------
# Marketplace Install / Update flow (MK4 + MK8 stubs)
# ---------------------------------------------------------------------------

marketplace_router = APIRouter(prefix="/api/marketplace/plugins", tags=["marketplace"])

# In-memory install tracking
_installs: dict[str, dict[str, str | int]] = {}


@marketplace_router.post("/{plugin_id}/install")
async def marketplace_install(plugin_id: str) -> dict[str, str]:
    """Start installing a marketplace plugin (stub).

    Returns an install_id that the frontend polls via the status endpoint.
    """
    install_id = str(uuid.uuid4())
    _installs[install_id] = {
        "install_id": install_id,
        "plugin_id": plugin_id,
        "status": "completed",
        "step": "done",
        "progress": 100,
    }
    return {"install_id": install_id}


@marketplace_router.get("/{plugin_id}/install/status")
async def marketplace_install_status(plugin_id: str) -> dict[str, Any]:
    """Poll the install progress for a plugin (stub).

    Returns completed immediately so the frontend advances to the success step.
    """
    # Find the latest install for this plugin
    for install in reversed(list(_installs.values())):
        if install["plugin_id"] == plugin_id:
            return {
                "status": install["status"],
                "step": install["step"],
                "progress": int(install["progress"]),
            }
    # If no install found, return completed anyway (idempotent stub)
    return {"status": "completed", "step": "done", "progress": 100}


@marketplace_router.post("/{plugin_id}/update")
async def marketplace_update(plugin_id: str) -> dict[str, str]:
    """Start updating a marketplace plugin to the latest version (stub).

    Behaves identically to install for now — returns an install_id.
    """
    install_id = str(uuid.uuid4())
    _installs[install_id] = {
        "install_id": install_id,
        "plugin_id": plugin_id,
        "status": "completed",
        "step": "done",
        "progress": 100,
    }
    return {"install_id": install_id}
