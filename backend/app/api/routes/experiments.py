"""API routes for experiment tracking."""

import math
import random
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


class ExperimentCreateSimple(BaseModel):
    """Simplified create payload used by the frontend modal."""

    name: str
    model: str
    epochs: int = 50
    learning_rate: float = 0.001
    batch_size: int = 32


class EpochLog(BaseModel):
    epoch: int
    metrics: dict[str, float]


class ExperimentCompareRequest(BaseModel):
    experiment_ids: list[uuid.UUID]


class EpochRead(BaseModel):
    epoch_number: int
    train_loss: float | None = None
    val_loss: float | None = None
    train_acc: float | None = None
    val_acc: float | None = None
    lr: float | None = None
    duration_s: float | None = None
    accuracy: float | None = None
    val_accuracy: float | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ExperimentRead(BaseModel):
    id: uuid.UUID
    name: str
    model: str = "ResNet-50"
    status: str
    config: dict[str, Any] = Field(default_factory=dict)
    workspace_id: uuid.UUID | None = None
    model_id: uuid.UUID | None = None
    best_epoch: int | None = None
    best_val_loss: float | None = None
    duration: str | None = None
    error_message: str | None = None
    epochs: list[EpochRead] = Field(default_factory=list)
    created_at: str | None = None

    class Config:
        from_attributes = True


# ---------- Mock data generator ----------


def _generate_mock_epochs(
    num_epochs: int,
    base_lr: float = 0.001,
) -> list[dict[str, Any]]:
    """Generate realistic training epoch data with decreasing loss curves."""
    epochs: list[dict[str, Any]] = []
    for i in range(1, num_epochs + 1):
        progress = i / num_epochs
        # Losses decrease with some noise
        train_loss = 2.5 * math.exp(-3.0 * progress) + random.gauss(0, 0.02)
        val_loss = 2.5 * math.exp(-2.8 * progress) + random.gauss(0, 0.03) + 0.05
        # Accuracy increases
        train_acc = min(1.0, 0.3 + 0.65 * (1 - math.exp(-3.5 * progress)) + random.gauss(0, 0.01))
        val_acc = min(1.0, 0.28 + 0.60 * (1 - math.exp(-3.0 * progress)) + random.gauss(0, 0.015))
        # LR schedule (cosine decay)
        lr = base_lr * 0.5 * (1 + math.cos(math.pi * progress))
        epochs.append({
            "epoch_number": i,
            "train_loss": round(max(0.01, train_loss), 4),
            "val_loss": round(max(0.01, val_loss), 4),
            "train_acc": round(max(0.0, min(1.0, train_acc)), 4),
            "val_acc": round(max(0.0, min(1.0, val_acc)), 4),
            "lr": round(lr, 6),
            "duration_s": round(random.uniform(12.0, 18.0), 1),
        })
    return epochs


def _build_mock_experiments() -> list[dict[str, Any]]:
    """Return a list of realistic mock experiments for frontend development."""
    experiments: list[dict[str, Any]] = []

    specs = [
        ("baseline-resnet50", "ResNet-50", "completed", 30, 0.001, 32),
        ("efficientnet-finetune", "EfficientNet-B0", "completed", 50, 0.0005, 64),
        ("vit-clip-transfer", "CLIP-ViT-B/32", "running", 20, 0.0001, 16),
        ("resnet101-augmented", "ResNet-101", "failed", 10, 0.01, 32),
        ("vit-base-scratch", "ViT-Base", "cancelled", 5, 0.001, 48),
    ]

    for name, model, exp_status, num_epochs, lr, bs in specs:
        epoch_data = _generate_mock_epochs(num_epochs, base_lr=lr)

        # Find best epoch (lowest val_loss)
        best_epoch = None
        best_val_loss = None
        for ep in epoch_data:
            vl = ep["val_loss"]
            if vl is not None and (best_val_loss is None or vl < best_val_loss):
                best_val_loss = vl
                best_epoch = ep["epoch_number"]

        total_duration_s = sum(ep.get("duration_s", 0) or 0 for ep in epoch_data)
        duration_str = f"{int(total_duration_s // 60)}m {int(total_duration_s % 60)}s"

        experiments.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "model": model,
            "status": exp_status,
            "config": {
                "epochs": num_epochs,
                "learning_rate": lr,
                "batch_size": bs,
            },
            "best_epoch": best_epoch,
            "best_val_loss": best_val_loss,
            "duration": duration_str,
            "error_message": "CUDA out of memory at epoch 10" if exp_status == "failed" else None,
            "epochs": epoch_data,
            "created_at": "2026-03-18T10:30:00Z",
        })

    return experiments


# Cache mock data so polling returns consistent results
_MOCK_EXPERIMENTS: list[dict[str, Any]] | None = None


def _get_mock_experiments() -> list[dict[str, Any]]:
    global _MOCK_EXPERIMENTS  # noqa: PLW0603
    if _MOCK_EXPERIMENTS is None:
        _MOCK_EXPERIMENTS = _build_mock_experiments()
    return _MOCK_EXPERIMENTS


# ---------- Endpoints ----------


@router.get("/mock")
async def list_experiments_mock() -> dict[str, Any]:
    """Return mock experiment data for frontend development.

    No DB dependency — use this endpoint while the DB layer is being built.
    """
    items = _get_mock_experiments()
    return {
        "items": items,
        "total": len(items),
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }


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


@router.post("/{experiment_id}/cancel")
async def cancel_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Cancel a running experiment."""
    try:
        await ExperimentService.cancel_experiment(db, experiment_id)
    except AttributeError:
        # Stub: service method not yet implemented
        pass
    except Exception:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"status": "cancelled"}


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an experiment and all its epoch data."""
    try:
        await ExperimentService.delete_experiment(db, experiment_id)
    except AttributeError:
        # Stub: service method not yet implemented
        pass
    except Exception:
        raise HTTPException(status_code=404, detail="Experiment not found")


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
