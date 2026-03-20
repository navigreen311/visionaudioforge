"""Dataset management API routes."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.dataset import (
    DatasetCreate,
    DatasetRead,
    SplitRequest,
    SplitResponse,
    UploadSummary,
)
from app.services.data.dataset_manager import DatasetService
from app.services.data.storage import MinIOStorageService

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _get_storage() -> MinIOStorageService:
    return MinIOStorageService()


def _dataset_to_read(d) -> DatasetRead:
    meta = d.metadata_ or {}
    return DatasetRead(
        id=d.id,
        name=d.name,
        modality=d.format,
        description=d.description,
        sample_count=d.item_count or 0,
        size_bytes=d.size_bytes or 0,
        version=meta.get("version", 1),
        stats=meta.get("stats"),
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


# ------------------------------------------------------------------
# POST /api/datasets
# ------------------------------------------------------------------
@router.post("", status_code=201)
async def create_dataset(
    body: DatasetCreate,
    db: AsyncSession = Depends(get_db),
) -> DatasetRead:
    dataset = await DatasetService.create_dataset(
        db, body.name, body.modality, body.workspace_id
    )
    return _dataset_to_read(dataset)


# ------------------------------------------------------------------
# GET /api/datasets
# ------------------------------------------------------------------
@router.get("")
async def list_datasets(
    workspace_id: uuid.UUID = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    items, total = await DatasetService.list_datasets(db, workspace_id, skip, limit)
    page = (skip // limit) + 1
    total_pages = max(1, (total + limit - 1) // limit)
    return PaginatedResponse(
        items=[_dataset_to_read(d) for d in items],
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
    )


# ------------------------------------------------------------------
# GET /api/datasets/{id}
# ------------------------------------------------------------------
@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DatasetRead:
    dataset = await DatasetService.get_dataset(db, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _dataset_to_read(dataset)


# ------------------------------------------------------------------
# POST /api/datasets/{id}/upload
# ------------------------------------------------------------------
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
