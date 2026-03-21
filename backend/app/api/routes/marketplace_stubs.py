"""Marketplace API stubs — browsing, installing, BYOM, widgets."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class PluginConfig(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class BYOMValidate(BaseModel):
    model_path: str = ""
    framework: str = "pytorch"


class BYOMRegister(BaseModel):
    name: str
    model_path: str = ""
    framework: str = "pytorch"
    description: str = ""


class WidgetGenerate(BaseModel):
    plugin_id: str
    widget_type: str = "embed"
    options: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Mock data helpers
# ---------------------------------------------------------------------------

def _mock_plugin(pid: str, name: str, **overrides: Any) -> dict:
    base = {
        "id": pid,
        "name": name,
        "version": "1.0.0",
        "author": "VisonAudioForge",
        "category": "vision",
        "rating": 4.5,
        "installs": 1200,
        "icon": f"/icons/{pid}.png",
        "tags": ["ai", "vision"],
    }
    base.update(overrides)
    return base


_FEATURED = [
    _mock_plugin("feat-1", "Auto-Label Pro", installs=3200, rating=4.8,
                 description="Automatic image labeling with CLIP"),
    _mock_plugin("feat-2", "Video Summarizer", installs=2100, rating=4.6,
                 description="AI-powered video summarization"),
    _mock_plugin("feat-3", "Data Augmentor", installs=4500, rating=4.9,
                 description="Smart data augmentation toolkit"),
]

_ALL_PLUGINS = _FEATURED + [
    _mock_plugin(f"plug-{i}", f"Plugin {i}",
                 installs=1000 - i * 30, category="audio" if i % 2 else "vision")
    for i in range(4, 25)
]

_INSTALLED = [
    {**_FEATURED[0], "installed": True, "enabled": True},
    {**_FEATURED[1], "installed": True, "enabled": True},
    {**_FEATURED[2], "installed": True, "enabled": False},
]

_BYOM_MODELS = [
    {
        "id": "byom-1",
        "name": "Custom ResNet Classifier",
        "framework": "pytorch",
        "status": "ready",
        "input_shape": [1, 3, 224, 224],
        "output_shape": [1, 10],
        "created_at": "2026-01-15T10:00:00Z",
    },
    {
        "id": "byom-2",
        "name": "Audio Emotion Detector",
        "framework": "tensorflow",
        "status": "ready",
        "input_shape": [1, 128, 64],
        "output_shape": [1, 7],
        "created_at": "2026-02-20T14:30:00Z",
    },
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/featured")
async def marketplace_featured() -> list[dict]:
    """Return 3 featured marketplace plugins."""
    return _FEATURED


@router.get("/plugins")
async def marketplace_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(8, ge=1, le=50),
    sort: str = Query("installs"),
    category: str = Query("all"),
) -> dict[str, Any]:
    """Paginated plugin listing."""
    pool = _ALL_PLUGINS
    if category != "all":
        pool = [p for p in pool if p.get("category") == category]
    if sort == "installs":
        pool = sorted(pool, key=lambda p: p["installs"], reverse=True)
    elif sort == "rating":
        pool = sorted(pool, key=lambda p: p.get("rating", 0), reverse=True)

    total = len(pool)
    start = (page - 1) * per_page
    items = pool[start : start + per_page]
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/plugins/{plugin_id}")
async def marketplace_plugin_detail(plugin_id: str) -> dict[str, Any]:
    """Extended plugin detail with description, features, requirements, changelog, reviews."""
    for p in _ALL_PLUGINS:
        if p["id"] == plugin_id:
            return {
                **p,
                "description": f"Full description for {p['name']}.",
                "features": [
                    "Real-time processing",
                    "Batch mode support",
                    "Custom model integration",
                ],
                "requirements": {
                    "min_version": "2.0.0",
                    "dependencies": ["numpy>=1.24", "torch>=2.0"],
                    "gpu_required": False,
                },
                "changelog": [
                    {"version": "1.0.0", "date": "2026-01-01", "notes": "Initial release"},
                    {"version": "0.9.0", "date": "2025-11-15", "notes": "Beta release"},
                ],
                "reviews": [
                    {"user": "alice", "rating": 5, "comment": "Excellent plugin!"},
                    {"user": "bob", "rating": 4, "comment": "Works well, needs docs."},
                ],
            }
    return {"error": "not_found", "plugin_id": plugin_id}


@router.post("/plugins/{plugin_id}/install")
async def marketplace_install(plugin_id: str) -> dict[str, str]:
    """Start plugin installation — returns a job ID."""
    return {"job_id": str(uuid.uuid4()), "plugin_id": plugin_id, "status": "started"}


@router.get("/plugins/{plugin_id}/install/status")
async def marketplace_install_status(plugin_id: str) -> dict[str, str]:
    """Check installation status — always returns complete for stub."""
    return {"plugin_id": plugin_id, "status": "complete"}


@router.delete("/plugins/{plugin_id}/install")
async def marketplace_uninstall(plugin_id: str) -> dict[str, Any]:
    """Uninstall a plugin."""
    return {"plugin_id": plugin_id, "status": "uninstalled", "success": True}


@router.patch("/plugins/{plugin_id}/config")
async def marketplace_plugin_config(plugin_id: str, body: PluginConfig) -> dict[str, Any]:
    """Update plugin configuration."""
    return {"plugin_id": plugin_id, "config": body.config, "success": True}


@router.post("/plugins/{plugin_id}/reviews")
async def marketplace_add_review(plugin_id: str, body: ReviewCreate) -> dict[str, Any]:
    """Submit a review for a plugin."""
    return {
        "plugin_id": plugin_id,
        "rating": body.rating,
        "comment": body.comment,
        "success": True,
    }


@router.post("/plugins/{plugin_id}/update")
async def marketplace_update_plugin(plugin_id: str) -> dict[str, str]:
    """Trigger plugin update."""
    return {"plugin_id": plugin_id, "status": "updated"}


@router.get("/installed")
async def marketplace_installed() -> list[dict]:
    """Return installed plugins — 3 mock entries."""
    return _INSTALLED


# ---------------------------------------------------------------------------
# BYOM (Bring Your Own Model)
# ---------------------------------------------------------------------------

@router.post("/byom/validate")
async def byom_validate(body: BYOMValidate) -> dict[str, Any]:
    """Validate a user-supplied model."""
    return {
        "valid": True,
        "framework": body.framework,
        "input_shape": [1, 3, 224, 224],
        "output_shape": [1, 10],
    }


@router.post("/byom/register")
async def byom_register(body: BYOMRegister) -> dict[str, Any]:
    """Register a BYOM model."""
    return {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "framework": body.framework,
        "status": "registered",
        "success": True,
    }


@router.get("/byom/models")
async def byom_models() -> list[dict]:
    """List registered BYOM models — 2 mock entries."""
    return _BYOM_MODELS


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

@router.post("/widgets/generate")
async def widget_generate(body: WidgetGenerate) -> dict[str, str]:
    """Generate an embeddable widget for a plugin."""
    return {
        "plugin_id": body.plugin_id,
        "widget_type": body.widget_type,
        "embed_code": (
            f'<iframe src="/widgets/{body.plugin_id}" '
            f'width="400" height="300" frameborder="0"></iframe>'
        ),
    }
