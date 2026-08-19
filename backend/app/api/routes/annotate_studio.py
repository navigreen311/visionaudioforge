"""Annotation Studio routes - lightweight stubs for the annotation UI.

These endpoints power the Annotation Studio frontend with mock data
until the real ML and persistence layers are wired up.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.data.annotation import AnnotationService

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


# NOTE: GET /api/annotate/assets is served by routes/annotations.py. This
# module registers first, so its bare-list version shadowed that one and the
# Annotate page - which sends workspace_id/dataset_id and reads `data.items` -
# got a payload it could not parse. The duplicate was removed.


@router.post("/auto-label", response_model=AutoLabelResponse)
async def auto_label(body: AutoLabelRequest):
    """Run mock auto-labelling on an asset and return suggestions."""
    return AutoLabelResponse(suggestions=[Suggestion(**s) for s in MOCK_SUGGESTIONS])


@router.post("/save", response_model=SaveResponse)
async def save_annotations(
    body: SaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist annotations for an asset.

    This returned `{"success": true, "count": N}` without writing anything: the
    studio reported a successful save and the work was gone on reload. The
    Annotation model and AnnotationService existed the whole time - this route
    simply never called them.
    """
    saved = 0
    for annotation in body.annotations:
        await AnnotationService.create_annotation(
            db=db,
            asset_id=uuid.UUID(body.asset_id),
            annotation_type=str(annotation.get("type", "bbox")),
            data=annotation,
            user_id=current_user.id,
        )
        saved += 1

    return SaveResponse(success=True, count=saved)


@router.post("/export", response_model=ExportResponse)
async def export_annotations(
    body: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export a dataset's annotations in COCO, YOLO or VOC form.

    This returned an empty list for every request, which is indistinguishable
    from a dataset with no annotations - so an export that silently lost
    everything looked like an export of nothing. AnnotationService already
    implements all three formats.
    """
    exported = await AnnotationService.export_annotations(
        db=db,
        dataset_id=uuid.UUID(body.dataset_id),
        format=body.format,
    )
    # The service returns the format's own document shape; hand back whatever
    # list it carries so the response stays a list, as the schema promises.
    if isinstance(exported, dict):
        payload = exported.get("annotations") or exported.get("images") or [exported]
    else:
        payload = exported
    return ExportResponse(format=body.format, annotations=payload)
