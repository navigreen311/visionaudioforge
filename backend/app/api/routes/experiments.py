"""API routes for experiment tracking."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.common import PaginatedResponse
from app.services.models.experiments import ExperimentService

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


# ---------- Schemas ----------


class ExperimentCreate(BaseModel):
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
    model_id: uuid.UUID | None = None
    workspace_id: uuid.UUID


class EpochLog(BaseModel):
    epoch: int
    metrics: dict[str, float]


class ExperimentCompareRequest(BaseModel):
    experiment_ids: list[uuid.UUID]


class EpochRead(BaseModel):
    epoch_number: int
    train_loss: float | None = None
    val_loss: float | None = None
    accuracy: float | None = None
    val_accuracy: float | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ExperimentRead(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    config: dict[str, Any] = Field(default_factory=dict)
    workspace_id: uuid.UUID
    model_id: uuid.UUID | None = None
    best_epoch: int | None = None
    error_message: str | None = None
    epochs: list[EpochRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ---------- Endpoints ----------


@router.get("")
async def list_experiments(
    workspace_id: uuid.UUID = Query(...),
    model_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    """List experiments for a workspace with optional model filter."""
    experiments, total = await ExperimentService.list_experiments(
        db, workspace_id, model_id=model_id, skip=skip, limit=limit
    )
    items = [ExperimentRead.model_validate(e).model_dump(mode="json") for e in experiments]
    total_pages = max(1, -(-total // limit))  # ceil division
    return PaginatedResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        total_pages=total_pages,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    body: ExperimentCreate,
    db: AsyncSession = Depends(get_db),
) -> ExperimentRead:
    """Create a new experiment."""
    experiment = await ExperimentService.create_experiment(
        db,
        name=body.name,
        config=body.config,
        model_id=body.model_id,
        workspace_id=body.workspace_id,
    )
    return ExperimentRead.model_validate(experiment)


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ExperimentRead:
    """Get experiment details with all epochs."""
    try:
        experiment = await ExperimentService.get_experiment(db, experiment_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentRead.model_validate(experiment)


@router.post("/{experiment_id}/epochs", status_code=status.HTTP_201_CREATED)
async def log_epoch(
    experiment_id: uuid.UUID,
    body: EpochLog,
    db: AsyncSession = Depends(get_db),
) -> EpochRead:
    """Log an epoch's metrics for an experiment."""
    try:
        epoch = await ExperimentService.log_epoch(
            db, experiment_id, body.epoch, body.metrics
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return EpochRead.model_validate(epoch)


@router.get("/{experiment_id}/best")
async def get_best_checkpoint(
    experiment_id: uuid.UUID,
    metric: str = Query("val_loss"),
    mode: str = Query("min"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the best checkpoint for an experiment by a given metric."""
    result = await ExperimentService.get_best_checkpoint(
        db, experiment_id, metric=metric, mode=mode
    )
    if not result:
        raise HTTPException(status_code=404, detail="No epochs found")
    return result


@router.post("/compare")
async def compare_experiments(
    body: ExperimentCompareRequest,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Compare multiple experiments side-by-side."""
    if len(body.experiment_ids) < 2:
        raise HTTPException(
            status_code=400, detail="At least 2 experiment IDs required"
        )
    return await ExperimentService.compare_experiments(db, body.experiment_ids)
