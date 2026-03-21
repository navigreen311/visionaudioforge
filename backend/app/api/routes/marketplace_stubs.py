"""Marketplace stub routes — browse, install, and manage marketplace items."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MarketplaceItem(BaseModel):
    id: str
    name: str
    category: str
    author: str
    description: str
    version: str
    downloads: int
    rating: float
    tags: list[str] = Field(default_factory=list)
    icon_url: str = ""
    installed: bool = False


class MarketplaceDetail(MarketplaceItem):
    readme: str = ""
    changelog: str = ""
    screenshots: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Mock catalogue
# ---------------------------------------------------------------------------

_CATALOGUE: list[dict[str, Any]] = [
    {
        "id": "mp-001", "name": "Auto-Label Pro", "category": "annotation",
        "author": "VisonAI", "description": "AI-powered auto-labeling for images and video.",
        "version": "2.1.0", "downloads": 4520, "rating": 4.7,
        "tags": ["annotation", "ai", "labeling"], "icon_url": "", "installed": False,
    },
    {
        "id": "mp-002", "name": "Spectral Denoiser", "category": "audio",
        "author": "AudioForge Labs", "description": "Real-time spectral noise reduction.",
        "version": "1.3.2", "downloads": 3100, "rating": 4.5,
        "tags": ["audio", "denoising", "spectral"], "icon_url": "", "installed": False,
    },
    {
        "id": "mp-003", "name": "Edge Deployer", "category": "deployment",
        "author": "VisonAI", "description": "One-click model deployment to edge devices.",
        "version": "3.0.0", "downloads": 2890, "rating": 4.8,
        "tags": ["edge", "deployment", "onnx"], "icon_url": "", "installed": True,
    },
    {
        "id": "mp-004", "name": "Dataset Augmenter", "category": "data",
        "author": "Community", "description": "Advanced augmentation pipelines for vision data.",
        "version": "1.0.5", "downloads": 1750, "rating": 4.2,
        "tags": ["augmentation", "data", "vision"], "icon_url": "", "installed": False,
    },
    {
        "id": "mp-005", "name": "Drift Monitor", "category": "monitoring",
        "author": "VisonAI", "description": "Track data and model drift in production.",
        "version": "2.0.1", "downloads": 2340, "rating": 4.6,
        "tags": ["monitoring", "drift", "mlops"], "icon_url": "", "installed": True,
    },
]

_installed: set[str] = {item["id"] for item in _CATALOGUE if item.get("installed")}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/items", response_model=list[MarketplaceItem])
async def list_items(
    category: str = Query("", description="Filter by category"),
    q: str = Query("", description="Search query"),
):
    """Browse marketplace items with optional filters."""
    results = list(_CATALOGUE)
    if category:
        results = [r for r in results if r["category"] == category]
    if q:
        q_lower = q.lower()
        results = [
            r for r in results
            if q_lower in r["name"].lower() or q_lower in r["description"].lower()
        ]
    return results


@router.get("/items/{item_id}", response_model=MarketplaceDetail)
async def get_item(item_id: str):
    """Get marketplace item details."""
    for item in _CATALOGUE:
        if item["id"] == item_id:
            return MarketplaceDetail(
                **item,
                readme=f"# {item['name']}\n\n{item['description']}",
                changelog="## v" + item["version"] + "\n- Initial marketplace release",
            )
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("/items/{item_id}/install")
async def install_item(item_id: str):
    """Install a marketplace item."""
    for item in _CATALOGUE:
        if item["id"] == item_id:
            _installed.add(item_id)
            item["installed"] = True
            return {"status": "installed", "id": item_id}
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("/items/{item_id}/uninstall")
async def uninstall_item(item_id: str):
    """Uninstall a marketplace item."""
    for item in _CATALOGUE:
        if item["id"] == item_id:
            _installed.discard(item_id)
            item["installed"] = False
            return {"status": "uninstalled", "id": item_id}
    raise HTTPException(status_code=404, detail="Item not found")


@router.get("/installed", response_model=list[MarketplaceItem])
async def list_installed():
    """List currently installed marketplace items."""
    return [item for item in _CATALOGUE if item["id"] in _installed]
