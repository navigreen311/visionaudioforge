"""Dataset management service — create, upload, split, stats, export."""

from __future__ import annotations

import json
import random
import uuid
from collections import defaultdict
from typing import Any

from fastapi import UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.dataset import Dataset
from app.services.data.storage import MinIOStorageService

BUCKET = "vaf-datasets"


def _dataset_modality(dataset: Any) -> str | None:
    """Read a dataset's modality.

    app/models/dataset.py calls the column `modality`; parts of this service and
    its tests were written against an earlier `format` column. Accept either
    rather than crashing on whichever one is absent.
    """
    return getattr(dataset, "modality", None) or getattr(dataset, "format", None)


def _asset_path(asset: Any) -> str | None:
    """Storage location of an asset.

    app/models/asset.py names the column `path`; older code and the test fakes
    use `storage_path`. Accept either.
    """
    return getattr(asset, "path", None) or getattr(asset, "storage_path", None)


class DatasetService:
    """High-level operations on datasets and their samples (assets)."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def create_dataset(
        db: AsyncSession,
        name: str,
        modality: str,
        workspace_id: uuid.UUID,
    ) -> Dataset:
        """Create a new dataset record."""
        dataset = Dataset(
            name=name,
            format=modality,
            description=f"{modality} dataset",
            item_count=0,
            size_bytes=0,
            metadata_={"modality": modality, "version": 1},
            workspace_id=workspace_id,
        )
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)
        return dataset

    @staticmethod
    async def list_datasets(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Dataset], int]:
        """Return paginated datasets for a workspace."""
        # Soft-delete flag lives in the Dataset.stats JSON column — the model has
        # no `metadata_` column, so referencing one raised AttributeError while
        # the statement was being built.
        base = select(Dataset).where(
            Dataset.workspace_id == workspace_id,
            Dataset.stats["archived"].as_boolean() != True,  # noqa: E712
        )
        total_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(total_q)).scalar() or 0

        rows = await db.execute(
            base.order_by(Dataset.created_at.desc()).offset(skip).limit(limit)
        )
        return list(rows.scalars().all()), total

    @staticmethod
    async def get_dataset(db: AsyncSession, dataset_id: uuid.UUID) -> Dataset | None:
        """Fetch a single dataset by id, with computed stats attached."""
        result = await db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset and not dataset.metadata_.get("stats"):
            # Lazy-compute stats if missing
            await DatasetService.compute_stats(db, dataset_id)
            await db.refresh(dataset)
        return dataset

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    @staticmethod
    async def upload_samples(
        db: AsyncSession,
        storage: MinIOStorageService,
        dataset_id: uuid.UUID,
        files: list[UploadFile],
        labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload files to MinIO and create Asset records."""
        dataset = await db.get(Dataset, dataset_id)
        if dataset is None:
            return {"uploaded": 0, "failed": 0, "errors": ["Dataset not found"]}

        uploaded = 0
        failed = 0
        errors: list[str] = []

        for f in files:
            try:
                data = await f.read()
                key = f"{dataset_id}/{f.filename}"
                url = await storage.upload_file(
                    bucket=BUCKET,
                    key=key,
                    file_data=data,
                    content_type=f.content_type or "application/octet-stream",
                )
                label = (labels or {}).get(f.filename)
                # Column names follow app/models/asset.py: type/path, not
                # media_type/storage_path. Passing the latter raised TypeError
                # for every file, so uploads silently reported 0 succeeded.
                asset = Asset(
                    filename=f.filename,
                    type=_dataset_modality(dataset),
                    path=url,
                    size_bytes=len(data),
                    metadata_={
                        "dataset_id": str(dataset_id),
                        "label": label,
                        "mime_type": f.content_type,
                    },
                    workspace_id=dataset.workspace_id,
                )
                db.add(asset)
                uploaded += 1
            except Exception as exc:
                failed += 1
                errors.append(f"{f.filename}: {exc}")

        # Update sample count
        dataset.item_count = (dataset.item_count or 0) + uploaded
        await db.commit()

        return {"uploaded": uploaded, "failed": failed, "errors": errors}

    # ------------------------------------------------------------------
    # Samples
    # ------------------------------------------------------------------

    @staticmethod
    async def list_samples(
        db: AsyncSession, dataset_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Return this dataset's samples with their storage path and label.

        This is the read path used by training (services/models/training.py) to
        fine-tune on uploaded data instead of synthetic tensors.
        """
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        return [
            {
                "id": str(a.id),
                "filename": a.filename,
                "storage_path": _asset_path(a),
                "label": (a.metadata_ or {}).get("label"),
                "split": (a.metadata_ or {}).get("split"),
                "size_bytes": a.size_bytes,
            }
            for a in assets
        ]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @staticmethod
    async def compute_stats(
        db: AsyncSession, dataset_id: uuid.UUID
    ) -> dict[str, Any]:
        """Compute and persist dataset statistics."""
        dataset = await db.get(Dataset, dataset_id)
        if dataset is None:
            return {}

        # Query all assets belonging to this dataset
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        total_samples = len(assets)
        total_size = sum(a.size_bytes or 0 for a in assets)

        modality_breakdown: dict[str, int] = defaultdict(int)
        label_distribution: dict[str, int] = defaultdict(int)

        for a in assets:
            modality_breakdown[a.media_type] += 1
            label = (a.metadata_ or {}).get("label")
            if label:
                label_distribution[label] += 1

        stats = {
            "total_samples": total_samples,
            "modality_breakdown": dict(modality_breakdown),
            "total_size_bytes": total_size,
            "label_distribution": dict(label_distribution),
        }

        meta = dict(dataset.metadata_ or {})
        meta["stats"] = stats
        dataset.metadata_ = meta
        dataset.item_count = total_samples
        dataset.size_bytes = total_size
        await db.commit()

        return stats

    # ------------------------------------------------------------------
    # Split
    # ------------------------------------------------------------------

    @staticmethod
    async def split_dataset(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        stratified: bool = True,
    ) -> dict[str, int]:
        """Split assets into train / val / test sets."""
        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        if not assets:
            return {"train": 0, "val": 0, "test": 0}

        def _assign(group: list[Asset]) -> dict[str, int]:
            random.shuffle(group)
            n = len(group)
            n_train = int(n * train_ratio)
            n_val = int(n * val_ratio)
            counts = {"train": 0, "val": 0, "test": 0}
            for i, asset in enumerate(group):
                if i < n_train:
                    split = "train"
                elif i < n_train + n_val:
                    split = "val"
                else:
                    split = "test"
                meta = dict(asset.metadata_ or {})
                meta["split"] = split
                asset.metadata_ = meta
                counts[split] += 1
            return counts

        totals = {"train": 0, "val": 0, "test": 0}

        if stratified:
            groups: dict[str | None, list[Asset]] = defaultdict(list)
            for a in assets:
                label = (a.metadata_ or {}).get("label")
                groups[label].append(a)
            for group in groups.values():
                counts = _assign(group)
                for k in totals:
                    totals[k] += counts[k]
        else:
            totals = _assign(assets)

        await db.commit()
        return totals

    # ------------------------------------------------------------------
    # Delete (soft)
    # ------------------------------------------------------------------

    @staticmethod
    async def delete_dataset(
        db: AsyncSession, dataset_id: uuid.UUID
    ) -> bool:
        """Soft-delete a dataset by marking it archived."""
        dataset = await db.get(Dataset, dataset_id)
        if dataset is None:
            return False
        meta = dict(dataset.metadata_ or {})
        meta["archived"] = True
        dataset.metadata_ = meta
        await db.commit()
        return True

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    @staticmethod
    async def export_dataset(
        db: AsyncSession,
        storage: MinIOStorageService,
        dataset_id: uuid.UUID,
        format: str = "json",
    ) -> bytes:
        """Export dataset metadata (and file paths) as JSON bytes."""
        dataset = await db.get(Dataset, dataset_id)
        if dataset is None:
            return b"{}"

        result = await db.execute(
            select(Asset).where(
                Asset.metadata_["dataset_id"].as_string() == str(dataset_id)
            )
        )
        assets = list(result.scalars().all())

        export_data = {
            "dataset": {
                "id": str(dataset.id),
                "name": dataset.name,
                "modality": dataset.format,
                "sample_count": dataset.item_count,
                "size_bytes": dataset.size_bytes,
                "stats": (dataset.metadata_ or {}).get("stats"),
            },
            "samples": [
                {
                    "id": str(a.id),
                    "filename": a.filename,
                    "media_type": a.media_type,
                    "size_bytes": a.size_bytes,
                    "storage_path": a.storage_path,
                    "label": (a.metadata_ or {}).get("label"),
                    "split": (a.metadata_ or {}).get("split"),
                }
                for a in assets
            ],
        }

        return json.dumps(export_data, indent=2).encode()
