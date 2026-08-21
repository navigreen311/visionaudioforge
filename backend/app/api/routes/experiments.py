"""API routes for experiment tracking.

Endpoints hit the database when available; if the DB is unreachable the list /
detail endpoints fall back to realistic mock data so the frontend always has
something to render.
"""

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


# Three fixture experiments and a `_mock_epochs` generator used to live here.
#
# `_mock_epochs` produced a training curve from `2.5 * exp(-3 * progress)` - a
# loss that falls smoothly to 0.05 and an accuracy that rises to 1.0, per epoch,
# with a decaying learning rate. It looked exactly like a successful training
# run because it was shaped like one, and the Train page drew it as a chart.
#
# Both endpoints below wrapped their database call in `except Exception` and fell
# back to it. That had three consequences, each worse than the last:
#
#   - `GET /api/experiments/{id}` never 404'd. Any UUID at all returned a
#     "completed" experiment named after the first eight characters of whatever
#     you asked for, with twenty epochs of invented metrics.
#   - the fixtures carried `workspace_id: 00000000-...-0000`, so what a tenant
#     saw was attributed to a workspace that is not theirs.
#   - a genuine database failure was indistinguishable from an empty list. The
#     catch-all swallowed it and answered 200.
#
# Deleted rather than made conditional. A fallback that fabricates is not a
# degraded mode, it is a wrong answer delivered confidently.


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

    experiments, total = await ExperimentService.list_experiments(
        db, workspace_id, model_id=model_id, skip=skip, limit=limit
    )
    items = [
        ExperimentRead.model_validate(e).model_dump(mode="json") for e in experiments
    ]
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
    # `get_experiment` ends in `scalar_one()`, so an unknown id raises rather
    # than returning None. Only that is caught: anything else is a real failure
    # and belongs in the 500, not hidden behind a fabricated 200.
    try:
        experiment = await ExperimentService.get_experiment(db, experiment_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Experiment not found") from None

    return ExperimentRead.model_validate(experiment).model_dump(mode="json")


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
