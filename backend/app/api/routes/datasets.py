"""Dataset management API routes."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_workspace_id
from app.schemas.common import PaginatedResponse
from app.schemas.dataset import (
    DatasetCreate,
    DatasetRead,
    DatasetSplitInfo,
    SplitRequest,
    SplitResponse,
    UploadSummary,
)
from app.services.data.active_learning import ActiveLearningService
from app.services.data.auto_labeling import AutoLabelingService
from app.services.data.dataset_manager import DatasetService
from app.services.data.quality_control import DatasetQualityService
from app.services.data.storage import MinIOStorageService
from app.services.data.synthetic import SyntheticDataGenerator

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _get_storage() -> MinIOStorageService:
    return MinIOStorageService()


def _dataset_to_read(d) -> DatasetRead:
    # The Dataset model has: name, modality, version, stats, workspace_id,
    # sample_count, created_at, updated_at.  Earlier code referenced
    # d.metadata_ / d.format / d.item_count / d.size_bytes / d.description
    # which don't exist on the model — use the actual columns with safe fallbacks.
    stats_raw = {}
    try:
        stats_raw = d.stats or {}
    except Exception:
        pass

    split_raw = stats_raw.get("split", {})
    class_counts_raw = (
        stats_raw.get("class_counts")
        or stats_raw.get("label_distribution")
        or {}
    )

    # Safely read attributes that may or may not exist on the ORM object
    modality = getattr(d, "modality", None) or getattr(d, "format", "image")
    sample_count = getattr(d, "sample_count", None) or getattr(d, "item_count", 0) or 0
    size_bytes = stats_raw.get("total_size_bytes", 0) or 0
    description = stats_raw.get("description", "") or ""
    version = getattr(d, "version", "1")

    return DatasetRead(
        id=d.id,
        name=d.name,
        modality=str(modality),
        description=description,
        sample_count=sample_count,
        size_bytes=size_bytes,
        version=version,
        split=DatasetSplitInfo(
            train=split_raw.get("train", 0),
            val=split_raw.get("val", 0),
            test=split_raw.get("test", 0),
        ),
        class_counts=class_counts_raw,
        stats=stats_raw if stats_raw else None,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


# ------------------------------------------------------------------
# POST /api/datasets
# ------------------------------------------------------------------
@router.post("", status_code=201)
async def create_dataset(
    body: DatasetCreate,
    workspace_id: uuid.UUID | None = Query(None),
    session_workspace: uuid.UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> DatasetRead:
    # The caller may still name a workspace in the body or the query, but it can
    # only ever be their own: TenantGuardMiddleware rejects a mismatch with 403
    # before the request reaches here. When they name none, the session's
    # workspace is the answer — never a default, and never someone else's.
    resolved = body.workspace_id or workspace_id or session_workspace

    dataset = await DatasetService.create_dataset(
        db, body.name, body.modality, resolved
    )
    return _dataset_to_read(dataset)


# ------------------------------------------------------------------
# GET /api/datasets
# ------------------------------------------------------------------
@router.get("")
async def list_datasets(
    workspace_id: uuid.UUID | None = Query(None),
    session_workspace: uuid.UUID = Depends(get_workspace_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    # There used to be a bare `except Exception` here that turned any failure
    # into an empty list. It hid a real defect for months: the archived filter
    # used `!= TRUE`, which is NULL for a fresh row, so a newly created dataset
    # never appeared in its own list — and the endpoint reported 200 with `[]`
    # rather than an error anyone could see. A list endpoint that cannot answer
    # must say so.
    items, total = await DatasetService.list_datasets(
        db, workspace_id or session_workspace, skip, limit
    )
    read_items = [_dataset_to_read(d) for d in items]
    page = (skip // limit) + 1
    total_pages = max(1, (total + limit - 1) // limit)
    return PaginatedResponse(
        items=read_items,
        total=total,
        page=page,
        size=limit,
        page_size=limit,
        total_pages=total_pages,
    )


# ------------------------------------------------------------------
# GET /api/datasets/{id}
# ------------------------------------------------------------------
@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: uuid.UUID,
    session_workspace: uuid.UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> DatasetRead:
    dataset = await DatasetService.get_dataset(db, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    # A path parameter names no workspace, so TenantGuardMiddleware cannot help
    # here — the row itself has to be checked. 404 rather than 403 on purpose: a
    # 403 would confirm that this id exists in some other tenant.
    if dataset.workspace_id != session_workspace:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _dataset_to_read(dataset)


# ------------------------------------------------------------------
# POST /api/datasets/{id}/upload
# ------------------------------------------------------------------
@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: uuid.UUID,
    session_workspace: uuid.UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a dataset.

    `DatasetsTab` has a delete button behind a confirmation dialog. It sent this
    to a path that only served GET, so FastAPI answered 405 and the row returned
    on the next refresh.
    """
    dataset = await DatasetService.get_dataset(db, dataset_id)
    if dataset is None or dataset.workspace_id != session_workspace:
        # 404 rather than 403, for the same reason as the getter above: a 403
        # would confirm this id exists in some other tenant.
        raise HTTPException(status_code=404, detail="Dataset not found")

    await db.delete(dataset)
    await db.commit()
    return Response(status_code=204)


@router.post("/{dataset_id}/upload")
async def upload_samples(
    dataset_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    labels: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
) -> UploadSummary:
    parsed_labels: dict[str, str] | None = None
    if labels:
        try:
            parsed_labels = json.loads(labels)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid labels JSON")

    result = await DatasetService.upload_samples(
        db, storage, dataset_id, files, parsed_labels
    )
    return UploadSummary(**result)


# ------------------------------------------------------------------
# POST /api/datasets/{id}/split
# ------------------------------------------------------------------
@router.post("/{dataset_id}/split")
async def split_dataset(
    dataset_id: uuid.UUID,
    body: SplitRequest,
    db: AsyncSession = Depends(get_db),
) -> SplitResponse:
    result = await DatasetService.split_dataset(
        db,
        dataset_id,
        train_ratio=body.train,
        val_ratio=body.val,
        test_ratio=body.test,
        stratified=body.stratified,
    )
    return SplitResponse(**result)


# ------------------------------------------------------------------
# POST /api/datasets/{id}/stats
# ------------------------------------------------------------------
@router.post("/{dataset_id}/stats")
async def compute_stats(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    stats = await DatasetService.compute_stats(db, dataset_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return stats


# ------------------------------------------------------------------
# GET /api/datasets/{id}/export
# ------------------------------------------------------------------
@router.get("/{dataset_id}/export")
async def export_dataset(
    dataset_id: uuid.UUID,
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
) -> Response:
    data = await DatasetService.export_dataset(db, storage, dataset_id, format)
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=dataset-{dataset_id}.json"},
    )


# ------------------------------------------------------------------
# POST /api/datasets/{id}/auto-label
# ------------------------------------------------------------------
@router.post("/{dataset_id}/auto-label")
async def auto_label_dataset(
    dataset_id: uuid.UUID,
    body: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run auto-labeling on unlabeled assets in the dataset."""
    body = body or {}
    model_name = body.get("model_name", "yolov8n")
    confidence_threshold = body.get("confidence_threshold", 0.7)
    result = await AutoLabelingService.auto_label_images(
        db, dataset_id, model_name=model_name, confidence_threshold=confidence_threshold
    )
    return result


# ------------------------------------------------------------------
# GET /api/datasets/{id}/quality
# ------------------------------------------------------------------
@router.get("/{dataset_id}/quality")
async def quality_report(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate a dataset health / quality report."""
    return await DatasetQualityService.generate_health_report(db, dataset_id)


# ------------------------------------------------------------------
# POST /api/datasets/{id}/duplicates
# ------------------------------------------------------------------
@router.post("/{dataset_id}/duplicates")
async def find_duplicates(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
) -> list[dict[str, Any]]:
    """Find near-duplicate samples in the dataset."""
    return await DatasetQualityService.find_near_duplicates(db, storage, dataset_id)


# ------------------------------------------------------------------
# POST /api/datasets/{id}/dedup
# ------------------------------------------------------------------
@router.post("/{dataset_id}/dedup")
async def deduplicate_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Remove duplicate samples from the dataset."""
    return await DatasetQualityService.deduplicate(db, dataset_id)


# ------------------------------------------------------------------
# POST /api/datasets/{id}/active-learning
# ------------------------------------------------------------------
@router.post("/{dataset_id}/active-learning")
async def active_learning_queue(
    dataset_id: uuid.UUID,
    body: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create an active-learning review queue."""
    body = body or {}
    strategy = body.get("strategy", "combined")
    k = body.get("k", 50)
    return await ActiveLearningService.create_review_queue(
        db, dataset_id, strategy=strategy, k=k
    )


# ------------------------------------------------------------------
# POST /api/datasets/{id}/synthetic
# ------------------------------------------------------------------
@router.post("/{dataset_id}/synthetic")
async def generate_synthetic(
    dataset_id: uuid.UUID,
    body: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
) -> dict[str, Any]:
    """Generate synthetic samples and add them to the dataset."""
    body = body or {}
    num = body.get("num", 10)
    pattern = body.get("pattern", "shapes")

    images = SyntheticDataGenerator.generate_synthetic_images(
        num=num, pattern=pattern
    )

    dataset = await DatasetService.get_dataset(db, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    added = 0
    for i, img in enumerate(images):
        import cv2
        import numpy as np

        success, encoded = cv2.imencode(".png", img)
        if not success:
            continue
        file_data = encoded.tobytes()
        key = f"{dataset_id}/synthetic_{pattern}_{i}.png"
        await storage.upload_file(
            bucket="vaf-datasets", key=key, file_data=file_data, content_type="image/png"
        )

        from app.models.asset import Asset as AssetModel

        asset = AssetModel(
            filename=f"synthetic_{pattern}_{i}.png",
            media_type=dataset.format,
            mime_type="image/png",
            size_bytes=len(file_data),
            storage_path=f"vaf-datasets/{key}",
            metadata_={
                "dataset_id": str(dataset_id),
                "synthetic": True,
                "pattern": pattern,
            },
            workspace_id=dataset.workspace_id,
        )
        db.add(asset)
        added += 1

    await db.commit()
    return {"generated": added, "pattern": pattern}
