"""Plugin Marketplace routes — registration, enable/disable, execution."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.plugin import Plugin, PluginReview as PluginReviewRow

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


class PluginReview(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=20)


class WidgetGenerateRequest(BaseModel):
    widget_type: str
    theme: str = "dark"
    width: int = 480
    height: int = 320
    refresh_interval: int = 5


# ---------------------------------------------------------------------------
# Storage
#
# Registrations live in the plugins table. A registration held in one worker's
# memory resolves on that process and 404s on the next.
# ---------------------------------------------------------------------------

def _plugin_out(plugin: Plugin) -> dict[str, Any]:
    return {
        "id": str(plugin.id),
        "name": plugin.name,
        "version": plugin.version,
        "description": plugin.description,
        "author": plugin.author,
        "entry_point": plugin.entry_point,
        "capabilities": (plugin.config_schema or {}).get("capabilities", []),
        "enabled": plugin.enabled,
        "installed_at": plugin.created_at.isoformat() if plugin.created_at else "",
    }


async def _load(db: AsyncSession, plugin_id: str) -> Plugin:
    try:
        key = uuid.UUID(plugin_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail="Plugin not found")

    result = await db.execute(select(Plugin).where(Plugin.id == key))
    plugin = result.scalar_one_or_none()
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", status_code=201)
async def register_plugin(
    body: PluginRegister,
    workspace_id: UUID | None = Query(None, description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Register a new plugin."""
    plugin = Plugin(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name=body.name,
        version=body.version,
        description=body.description,
        author=body.author,
        category="integration",
        entry_point=body.entry_point,
        permissions=[],
        config_schema={"capabilities": body.capabilities},
        config={},
        enabled=False,
        status="registered",
    )
    db.add(plugin)
    await db.commit()
    await db.refresh(plugin)
    return _plugin_out(plugin)


@router.get("/")
async def list_plugins(
    workspace_id: UUID | None = Query(None, description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List registered plugins, scoped to a workspace when given."""
    query = select(Plugin)
    if workspace_id is not None:
        query = query.where(Plugin.workspace_id == workspace_id)

    result = await db.execute(query.order_by(Plugin.created_at))
    return [_plugin_out(p) for p in result.scalars().all()]


@router.get("/{plugin_id}")
async def get_plugin(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get plugin details."""
    return _plugin_out(await _load(db, plugin_id))


@router.post("/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Enable a plugin."""
    plugin = await _load(db, plugin_id)
    plugin.enabled = True
    await db.commit()
    return {"plugin_id": plugin_id, "enabled": True}


@router.post("/{plugin_id}/disable")
async def disable_plugin(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Disable a plugin."""
    plugin = await _load(db, plugin_id)
    plugin.enabled = False
    await db.commit()
    return {"plugin_id": plugin_id, "enabled": False}


@router.post("/{plugin_id}/execute")
async def execute_plugin(
    plugin_id: str,
    body: PluginExecute,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Execute a plugin action."""
    plugin = await _load(db, plugin_id)
    if not plugin.enabled:
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
# Review endpoints
# ---------------------------------------------------------------------------

def _review_out(review: PluginReviewRow) -> dict[str, Any]:
    return {
        "id": str(review.id),
        "plugin_id": str(review.plugin_id),
        "rating": int(review.rating),
        "text": review.comment,
        "created_at": review.created_at.isoformat() if review.created_at else "",
    }


@router.post("/{plugin_id}/reviews", status_code=201)
async def submit_review(
    plugin_id: str,
    body: PluginReview,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Submit a review for a plugin."""
    plugin = await _load(db, plugin_id)

    review = PluginReviewRow(
        id=uuid.uuid4(),
        plugin_id=plugin.id,
        rating=float(body.rating),
        comment=body.text,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return _review_out(review)


@router.get("/{plugin_id}/reviews")
async def list_reviews(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List reviews for a plugin, oldest first."""
    plugin = await _load(db, plugin_id)

    result = await db.execute(
        select(PluginReviewRow)
        .where(PluginReviewRow.plugin_id == plugin.id)
        .order_by(PluginReviewRow.created_at)
    )
    return [_review_out(r) for r in result.scalars().all()]


# ---------------------------------------------------------------------------
# Widget embed generation
# ---------------------------------------------------------------------------

@router.post("/widgets/generate")
async def generate_widget(body: WidgetGenerateRequest) -> dict[str, Any]:
    """Generate an embeddable widget token and URL."""
    token = str(uuid.uuid4())
    url = f"https://app.vaf.io/embed/{body.widget_type}?token={token}"
    return {
        "widget_type": body.widget_type,
        "token": token,
        "embed_url": url,
        "config": {
            "theme": body.theme,
            "width": body.width,
            "height": body.height,
            "refresh_interval": body.refresh_interval,
        },
    }
