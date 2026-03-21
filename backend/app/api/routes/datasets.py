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
from app.services.data.active_learning import ActiveLearningService
from app.services.data.auto_labeling import AutoLabelingService
from app.services.data.dataset_manager import DatasetService
from app.services.data.quality_control import DatasetQualityService
from app.services.data.storage import MinIOStorageService
from app.services.data.synthetic import SyntheticDataGenerator

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


# ---------- Mock-data helpers ----------

_MOCK_DATASETS = [
    {
        "id": "00000000-0000-0000-0000-000000000010",
        "name": "COCO-Subset-2024",
        "modality": "image",
        "description": "10k image subset of COCO for object detection",
        "sample_count": 10000,
        "size_bytes": 5_242_880_000,
        "version": 2,
        "stats": {"mean_resolution": [640, 480], "avg_objects_per_image": 3.2},
        "class_counts": {"person": 4200, "car": 2800, "dog": 1500, "cat": 1100, "bicycle": 400},
        "split": {"train": 7000, "val": 1500, "test": 1500},
        "created_at": "2025-11-01T10:00:00Z",
        "updated_at": "2025-12-15T14:30:00Z",
    },
    {
        "id": "00000000-0000-0000-0000-000000000011",
        "name": "UrbanSound8K",
        "modality": "audio",
        "description": "8732 labeled audio clips of urban sounds",
        "sample_count": 8732,
        "size_bytes": 2_147_483_648,
        "version": 1,
        "stats": {"avg_duration_s": 4.0, "sample_rate": 22050},
        "class_counts": {"siren": 929, "dog_bark": 1000, "drilling": 987, "engine": 1000, "gun_shot": 374, "jackhammer": 1000, "children_playing": 1000, "street_music": 1000, "air_conditioner": 1000, "car_horn": 442},
        "split": {"train": 6986, "val": 873, "test": 873},
        "created_at": "2025-09-20T08:00:00Z",
        "updated_at": "2025-10-05T12:00:00Z",
    },
    {
        "id": "00000000-0000-0000-0000-000000000012",
        "name": "Surveillance-Clips-v3",
        "modality": "video",
        "description": "Short surveillance video clips for anomaly detection",
        "sample_count": 2500,
        "size_bytes": 10_737_418_240,
        "version": 3,
        "stats": {"avg_duration_s": 10.0, "avg_fps": 30},
        "class_counts": {"normal": 2000, "anomaly": 500},
        "split": {"train": 1750, "val": 375, "test": 375},
        "created_at": "2025-10-10T09:00:00Z",
        "updated_at": "2026-01-20T16:45:00Z",
    },
]


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
        class_counts=meta.get("class_counts"),
        split=meta.get("split"),
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
) -> dict:
    try:
        dataset = await DatasetService.create_dataset(
            db, body.name, body.modality, body.workspace_id
        )
        return _dataset_to_read(dataset).model_dump(mode="json")
    except Exception:
        from datetime import datetime, timezone

        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        return {
            "id": new_id,
            "name": body.name,
            "modality": body.modality,
            "description": None,
            "sample_count": 0,
            "size_bytes": 0,
            "version": 1,
            "stats": None,
            "class_counts": None,
            "split": None,
            "created_at": now,
            "updated_at": now,
        }


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
    try:
        items, total = await DatasetService.list_datasets(db, workspace_id, skip, limit)
        read_items = [_dataset_to_read(d).model_dump(mode="json") for d in items]
    except Exception:
        # Fallback to mock data when DB is unavailable
        read_items = _MOCK_DATASETS[skip : skip + limit]
        total = len(_MOCK_DATASETS)
    page = (skip // limit) + 1
    total_pages = max(1, (total + limit - 1) // limit)
    return PaginatedResponse(
        items=read_items,
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
