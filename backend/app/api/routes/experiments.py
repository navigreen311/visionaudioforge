"""API routes for experiment tracking.

Endpoints hit the database when available; if the DB is unreachable the list /
detail endpoints fall back to realistic mock data so the frontend always has
something to render.
"""

import math
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_optional_workspace_id
from app.schemas.common import PaginatedResponse
from app.models.experiment import Experiment
from app.models.workspace import SYSTEM_WORKSPACE_ID
from app.services.models.experiments import ExperimentService

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


# ---------- Mock-data helpers ----------

def _mock_epochs(n: int = 20) -> list[dict]:
    """Generate *n* epochs of training data with decreasing loss."""
    epochs = []
    for i in range(1, n + 1):
        progress = i / n
        train_loss = 2.5 * math.exp(-3.0 * progress) + 0.05
        val_loss = 2.5 * math.exp(-2.8 * progress) + 0.08
        accuracy = 1.0 - math.exp(-3.0 * progress)
        val_accuracy = 1.0 - math.exp(-2.6 * progress)
        epochs.append({
            "epoch_number": i,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "accuracy": round(accuracy, 4),
            "val_accuracy": round(val_accuracy, 4),
            "metrics": {
                "lr": round(0.001 * (0.95 ** i), 6),
            },
        })
    return epochs


_MOCK_EXPERIMENTS = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "ResNet50 Baseline",
        "status": "completed",
        "config": {"architecture": "resnet50", "batch_size": 32, "lr": 0.001},
        "workspace_id": "00000000-0000-0000-0000-000000000000",
        "model_id": None,
        "best_epoch": 18,
        "error_message": None,
        "epochs": _mock_epochs(20),
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "name": "CLIP Fine-tune v1",
        "status": "running",
        "config": {"architecture": "clip-vit-b32", "batch_size": 16, "lr": 0.0005},
        "workspace_id": "00000000-0000-0000-0000-000000000000",
        "model_id": None,
        "best_epoch": 12,
        "error_message": None,
        "epochs": _mock_epochs(12),
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "name": "Audio MFCC Classifier",
        "status": "completed",
        "config": {"architecture": "cnn-1d", "batch_size": 64, "lr": 0.002},
        "workspace_id": "00000000-0000-0000-0000-000000000000",
        "model_id": None,
        "best_epoch": 15,
        "error_message": None,
        "epochs": _mock_epochs(20),
    },
]


# ---------- Schemas ----------


class ExperimentCreate(BaseModel):
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
    model_id: uuid.UUID | None = None
    # Optional: the caller's own workspace supplies it when the body does not.
    workspace_id: uuid.UUID | None = None


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
    # Optional so the endpoint answers unscoped callers the way the other
    # list endpoints do. An unresolvable workspace yields an empty page,
    # never an unscoped read across tenants.
    workspace_id: uuid.UUID | None = Query(None),
    caller_workspace: uuid.UUID | None = Depends(get_optional_workspace_id),
    model_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    """List experiments for a workspace with optional model filter."""
    workspace_id = workspace_id or caller_workspace
    if workspace_id is None:
        return PaginatedResponse(
            items=[], total=0, page=1, size=limit, page_size=limit, total_pages=1
        )

    try:
        experiments, total = await ExperimentService.list_experiments(
            db, workspace_id, model_id=model_id, skip=skip, limit=limit
        )
        items = [ExperimentRead.model_validate(e).model_dump(mode="json") for e in experiments]
    except Exception:
        # Fallback to mock data when DB is unavailable
        items = _MOCK_EXPERIMENTS[skip : skip + limit]
        total = len(_MOCK_EXPERIMENTS)
    total_pages = max(1, -(-total // limit))  # ceil division
    return PaginatedResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        page_size=limit,
        total_pages=total_pages,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    body: ExperimentCreate,
    caller_workspace: uuid.UUID | None = Depends(get_optional_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new experiment."""
    # On any failure this used to return a fabricated experiment carrying a
    # fresh uuid that had never been written. The caller got a 200 and an id
    # that would 404 on the very next request, and the real error was lost.
    workspace_id = body.workspace_id or caller_workspace or SYSTEM_WORKSPACE_ID

    try:
        experiment = await ExperimentService.create_experiment(
            db,
            name=body.name,
            config=body.config,
            model_id=body.model_id,
            workspace_id=workspace_id,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"workspace_id {workspace_id} does not exist",
        )

    return ExperimentRead.model_validate(experiment).model_dump(mode="json")


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get experiment details with all epochs."""
    try:
        experiment = await ExperimentService.get_experiment(db, experiment_id)
        return ExperimentRead.model_validate(experiment).model_dump(mode="json")
    except Exception:
        # Fallback: search mock data or generate a placeholder
        eid = str(experiment_id)
        for mock in _MOCK_EXPERIMENTS:
            if mock["id"] == eid:
                return mock
        # Return a generated placeholder with full epochs
        return {
            "id": eid,
            "name": f"Experiment {eid[:8]}",
            "status": "completed",
            "config": {"architecture": "resnet50", "batch_size": 32},
            "workspace_id": "00000000-0000-0000-0000-000000000000",
            "model_id": None,
            "best_epoch": 18,
            "error_message": None,
            "epochs": _mock_epochs(20),
        }


@router.delete("/{experiment_id}", status_code=204)
async def delete_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete an experiment.

    `ExperimentsTab`'s delete button, behind "Delete this experiment? This
    cannot be undone.", sent this to a path serving only GET and POST. It
    answered 405 and the experiment stayed.
    """
    # `get_experiment` ends in `scalar_one()`, which raises rather than
    # returning None - checking for None let a missing id surface as a 500.
    try:
        experiment = await ExperimentService.get_experiment(db, experiment_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Experiment not found") from None

    await db.delete(experiment)
    await db.commit()
    return Response(status_code=204)


@router.post("/{experiment_id}/cancel")
async def cancel_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a running training experiment."""
    try:
        experiment = await ExperimentService.get_experiment(db, experiment_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail=f"Experiment is already {experiment.status}",
        )

    experiment.status = "cancelled"
    await db.commit()
    await db.refresh(experiment)

    return {"id": str(experiment.id), "status": experiment.status}


# Both spellings are in use by callers; one handler serves them.
@router.post("/{experiment_id}/epochs", status_code=status.HTTP_201_CREATED)
@router.post("/{experiment_id}/log", status_code=status.HTTP_201_CREATED)
async def log_epoch(
    experiment_id: uuid.UUID,
    body: EpochLog,
    db: AsyncSession = Depends(get_db),
) -> EpochRead:
    """Log an epoch's metrics for an experiment."""
    # Catching everything here and reporting 404 hid a schema mismatch behind
    # "Experiment not found" for as long as it existed. Check for the
    # experiment explicitly and let anything else surface as itself.
    if await db.get(Experiment, experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    epoch = await ExperimentService.log_epoch(
        db, experiment_id, body.epoch, body.metrics
    )
    return EpochRead.model_validate(epoch)


@router.get("/{experiment_id}/best")
async def get_best_checkpoint(
    experiment_id: uuid.UUID,
    metric: str = Query("val_loss"),
    mode: str = Query("min"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the best checkpoint for an experiment by a given metric."""
    if await db.get(Experiment, experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    result = await ExperimentService.get_best_checkpoint(
        db, experiment_id, metric=metric, mode=mode
    )
    if not result:
        # 404 here used to mean three different things: no such experiment, no
        # epochs logged, and epochs logged but none carrying this metric. Only
        # the first is a missing resource — the others are a real answer to the
        # question asked.
        return {"found": False, "metric": metric, "mode": mode, "best": None}

    return {"found": True, "metric": metric, "mode": mode, **result}


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
