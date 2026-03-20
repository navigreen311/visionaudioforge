"""Model Registry Service — lifecycle management for ML model records."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_registry import ModelRecord

# Valid lifecycle transitions: source_status -> set of allowed target statuses
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "registered": {"staging", "archived"},
    "staging": {"production", "archived"},
    "production": {"archived"},
    "archived": set(),  # terminal state (except rollback)
}


class ModelRegistryService:
    """Manages model registration, lifecycle transitions, comparison, and rollback."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def register_model(
        db: AsyncSession,
        name: str,
        version: str,
        backbone: str | None,
        metrics: dict | None,
        workspace_id: UUID,
    ) -> ModelRecord:
        """Create a new model record with status='registered'."""
        record = ModelRecord(
            name=name,
            version=version,
            backbone=backbone,
            metrics=metrics or {},
            workspace_id=workspace_id,
            status="registered",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_model(db: AsyncSession, model_id: UUID) -> ModelRecord:
        """Return a single model or raise 404."""
        result = await db.execute(
            select(ModelRecord).where(ModelRecord.id == model_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_id} not found",
            )
        return record

    @staticmethod
    async def list_models(
        db: AsyncSession,
        workspace_id: UUID,
        model_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ModelRecord], int]:
        """Return paginated model list with total count."""
        base = select(ModelRecord).where(ModelRecord.workspace_id == workspace_id)
        count_q = select(func.count()).select_from(ModelRecord).where(
            ModelRecord.workspace_id == workspace_id
        )

        if model_status:
            base = base.where(ModelRecord.status == model_status)
            count_q = count_q.where(ModelRecord.status == model_status)

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(base.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    async def update_status(
        db: AsyncSession,
        model_id: UUID,
        new_status: str,
    ) -> ModelRecord:
        """Transition model status respecting lifecycle rules."""
        record = await ModelRegistryService.get_model(db, model_id)
        current = record.status
        allowed = _VALID_TRANSITIONS.get(current, set())

        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition: {current} -> {new_status}",
            )

        record.status = new_status
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def delete_model(db: AsyncSession, model_id: UUID) -> ModelRecord:
        """Soft-delete by setting status to 'archived'."""
        record = await ModelRegistryService.get_model(db, model_id)
        record.status = "archived"
        await db.commit()
        await db.refresh(record)
        return record

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    @staticmethod
    async def compare_models(
        db: AsyncSession,
        model_id_a: UUID,
        model_id_b: UUID,
    ) -> dict:
        """Side-by-side metric comparison of two models."""
        model_a = await ModelRegistryService.get_model(db, model_id_a)
        model_b = await ModelRegistryService.get_model(db, model_id_b)

        metrics_a: dict = model_a.metrics or {}
        metrics_b: dict = model_b.metrics or {}

        all_keys = set(metrics_a.keys()) | set(metrics_b.keys())
        metric_diffs = {}
        for key in sorted(all_keys):
            val_a = metrics_a.get(key)
            val_b = metrics_b.get(key)
            diff = None
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                diff = round(val_b - val_a, 6)
            metric_diffs[key] = {"model_a": val_a, "model_b": val_b, "diff": diff}

        return {
            "model_a": {
                "id": str(model_a.id),
                "name": model_a.name,
                "version": model_a.version,
                "metrics": metrics_a,
            },
            "model_b": {
                "id": str(model_b.id),
                "name": model_b.name,
                "version": model_b.version,
                "metrics": metrics_b,
            },
            "metric_diffs": metric_diffs,
        }

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    @staticmethod
    async def rollback(
        db: AsyncSession,
        model_id: UUID,
        to_version: str,
    ) -> ModelRecord:
        """Rollback: find the target version, promote it to 'production', demote current production."""
        record = await ModelRegistryService.get_model(db, model_id)

        # Find the target version within the same model name / workspace
        result = await db.execute(
            select(ModelRecord).where(
                ModelRecord.name == record.name,
                ModelRecord.workspace_id == record.workspace_id,
                ModelRecord.version == to_version,
            )
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {to_version} not found for model '{record.name}'",
            )

        # Demote any current production versions of this model name in same workspace
        await db.execute(
            update(ModelRecord)
            .where(
                ModelRecord.name == record.name,
                ModelRecord.workspace_id == record.workspace_id,
                ModelRecord.status == "production",
            )
            .values(status="archived")
        )

        # Promote target version
        target.status = "production"
        await db.commit()
        await db.refresh(target)
        return target
