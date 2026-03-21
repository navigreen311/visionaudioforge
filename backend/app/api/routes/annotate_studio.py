"""Annotation Studio routes — lightweight stubs for the annotation UI.

These endpoints power the Annotation Studio frontend with mock data
until the real ML and persistence layers are wired up.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/annotate", tags=["annotate-studio"])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------


class AssetItem(BaseModel):
    id: str
    filename: str
    thumbnail_b64: str | None = None
    type: str


class BBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class Suggestion(BaseModel):
    label: str
    confidence: float
    bbox: BBox


class AutoLabelRequest(BaseModel):
    asset_id: str
    model: str = "default"


class AutoLabelResponse(BaseModel):
    suggestions: list[Suggestion]


class SaveRequest(BaseModel):
    asset_id: str
    annotations: list[dict[str, Any]]


class SaveResponse(BaseModel):
    success: bool
    count: int


class ExportRequest(BaseModel):
    dataset_id: str
    format: str = "coco"
    asset_ids: list[str] = Field(default_factory=list)


class ExportResponse(BaseModel):
    format: str
    annotations: list[Any]


# ------------------------------------------------------------------
# Mock data
# ------------------------------------------------------------------

MOCK_ASSETS: list[dict[str, Any]] = [
    {"id": "asset-001", "filename": "street_view_001.jpg", "thumbnail_b64": None, "type": "image"},
    {"id": "asset-002", "filename": "parking_lot_002.png", "thumbnail_b64": None, "type": "image"},
    {"id": "asset-003", "filename": "warehouse_cam_003.jpg", "thumbnail_b64": None, "type": "image"},
    {"id": "asset-004", "filename": "drone_flyover_004.mp4", "thumbnail_b64": None, "type": "video"},
    {"id": "asset-005", "filename": "traffic_intersection_005.jpg", "thumbnail_b64": None, "type": "image"},
    {"id": "asset-006", "filename": "retail_floor_006.png", "thumbnail_b64": None, "type": "image"},
]

MOCK_SUGGESTIONS: list[dict[str, Any]] = [
    {"label": "person", "confidence": 0.91, "bbox": {"x": 120, "y": 80, "width": 90, "height": 200}},
    {"label": "car", "confidence": 0.85, "bbox": {"x": 300, "y": 150, "width": 120, "height": 80}},
    {"label": "dog", "confidence": 0.72, "bbox": {"x": 50, "y": 200, "width": 60, "height": 50}},
]


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@router.get("/assets", response_model=list[AssetItem])
async def list_annotate_assets():
    """Return mock assets available for annotation."""
    return MOCK_ASSETS


@router.post("/auto-label", response_model=AutoLabelResponse)
async def auto_label(body: AutoLabelRequest):
    """Run mock auto-labelling on an asset and return suggestions."""
    return AutoLabelResponse(suggestions=[Suggestion(**s) for s in MOCK_SUGGESTIONS])


@router.post("/save", response_model=SaveResponse)
async def save_annotations(body: SaveRequest):
    """Persist annotations for an asset (stub — returns success)."""
    return SaveResponse(success=True, count=len(body.annotations))


@router.post("/export", response_model=ExportResponse)
async def export_annotations(body: ExportRequest):
    """Export annotations in the requested format (stub — returns empty list)."""
    return ExportResponse(format=body.format, annotations=[])
