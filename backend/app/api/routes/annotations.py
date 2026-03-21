"""Annotation management routes — CRUD, export, import, stats."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_db
from app.schemas.annotation import (
    AnnotationCreate,
    AnnotationImport,
    AnnotationRead,
    AnnotationStatsResponse,
    AnnotationUpdate,
)
from app.services.data.annotation import AnnotationService

router = APIRouter(prefix="/api", tags=["annotations"])


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------


@router.post("/annotations", response_model=AnnotationRead)
async def create_annotation(body: AnnotationCreate, db=Depends(get_db)):
    """Create a new annotation for an asset."""
    try:
        annotation = await AnnotationService.create_annotation(
            db=db,
            asset_id=body.asset_id,
            annotation_type=body.annotation_type,
            data=body.data,
            user_id=body.user_id,
            dataset_id=body.dataset_id,
        )
        return AnnotationRead.model_validate(annotation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/annotations", response_model=list[AnnotationRead])
async def get_annotations(asset_id: UUID = Query(...), db=Depends(get_db)):
    """Get all annotations for a specific asset."""
    annotations = await AnnotationService.get_annotations(db, asset_id)
    return [AnnotationRead.model_validate(a) for a in annotations]


@router.put("/annotations/{annotation_id}", response_model=AnnotationRead)
async def update_annotation(
    annotation_id: UUID,
    body: AnnotationUpdate,
    db=Depends(get_db),
):
    """Update an annotation's data."""
    try:
        annotation = await AnnotationService.update_annotation(db, annotation_id, body.data)
        return AnnotationRead.model_validate(annotation)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(annotation_id: UUID, db=Depends(get_db)):
    """Delete an annotation."""
    deleted = await AnnotationService.delete_annotation(db, annotation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return {"deleted": True}


# ------------------------------------------------------------------
# Dataset-level operations
# ------------------------------------------------------------------


@router.get("/datasets/{dataset_id}/annotations", response_model=list[AnnotationRead])
async def get_dataset_annotations(dataset_id: UUID, db=Depends(get_db)):
    """Get all annotations for a dataset."""
    annotations = await AnnotationService.get_dataset_annotations(db, dataset_id)
    return [AnnotationRead.model_validate(a) for a in annotations]


@router.post("/datasets/{dataset_id}/annotations/export")
async def export_annotations(
    dataset_id: UUID,
    format: str = Query("coco", pattern="^(coco|yolo|voc)$"),
    db=Depends(get_db),
):
    """Export dataset annotations in COCO, YOLO, or VOC format."""
    try:
        result = await AnnotationService.export_annotations(db, dataset_id, format=format)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/datasets/{dataset_id}/annotations/import")
async def import_annotations(
    dataset_id: UUID,
    body: AnnotationImport,
    db=Depends(get_db),
):
    """Import annotations from COCO format."""
    try:
        result = await AnnotationService.import_annotations(
            db, dataset_id, body.data, format=body.format,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/datasets/{dataset_id}/annotations/stats", response_model=AnnotationStatsResponse)
async def annotation_stats(dataset_id: UUID, db=Depends(get_db)):
    """Get annotation statistics for a dataset."""
    stats = await AnnotationService.annotation_stats(db, dataset_id)
    return AnnotationStatsResponse(**stats)


# ------------------------------------------------------------------
# Annotate page helpers
# ------------------------------------------------------------------


@router.get("/annotate/assets")
async def get_annotate_assets(
    dataset_id: UUID = Query(...),
    workspace_id: UUID = Query(...),
):
    """Return mock asset list for the annotation page thumbnail strip.

    TODO: Replace with real DB query joining assets to the dataset.
    """
    mock_assets = [
        {
            "id": f"a{i:04d}-0000-0000-0000-000000000000",
            "filename": f"image_{i:03d}.jpg",
            "path": f"/data/images/image_{i:03d}.jpg",
            "type": "image",
            "thumbnail_url": None,
            "annotation_count": (i * 3) % 5,
        }
        for i in range(1, 21)
    ]
    return {"items": mock_assets, "total": len(mock_assets)}
