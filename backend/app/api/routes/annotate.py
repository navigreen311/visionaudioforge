"""Annotate workspace routes — save & export stubs for the annotation UI."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/annotate", tags=["annotate"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class AnnotationPayload(BaseModel):
    id: str
    label: str
    type: str
    color: str
    coordinates: dict[str, object]
    confidence: Optional[float] = None
    ai_suggested: bool = False


class SaveRequest(BaseModel):
    asset_id: str
    annotations: list[AnnotationPayload]


class SaveResponse(BaseModel):
    saved: bool
    asset_id: str
    count: int
    message: str


class ExportRequest(BaseModel):
    dataset_id: str
    format: str = Field(default="coco_json", pattern=r"^(coco_json|yolo_txt|pascal_voc_xml|csv)$")
    asset_ids: list[str] = Field(default_factory=list)
    current_only: bool = False


class ExportResponse(BaseModel):
    format: str
    download_url: Optional[str] = None
    message: str
    success: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/save", response_model=SaveResponse)
async def save_annotations(body: SaveRequest) -> SaveResponse:
    """Persist annotations for a single asset (auto-save target).

    This is a placeholder stub. The real implementation will write to the
    database via AnnotationService.
    """
    return SaveResponse(
        saved=True,
        asset_id=body.asset_id,
        count=len(body.annotations),
        message=f"Saved {len(body.annotations)} annotation(s) for asset {body.asset_id}.",
    )


@router.post("/export", response_model=ExportResponse)
async def export_annotations(body: ExportRequest) -> ExportResponse:
    """Export annotations in the requested format.

    This is a placeholder stub. The real implementation will generate
    the export file and return a download URL.
    """
    asset_scope = "current image" if body.current_only else f"{len(body.asset_ids)} asset(s)"
    return ExportResponse(
        format=body.format,
        download_url=None,
        message=f"Export ({body.format}) requested for {asset_scope} in dataset {body.dataset_id}.",
        success=True,
    )
