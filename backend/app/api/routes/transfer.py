"""API routes for transfer learning / fine-tuning."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.models.experiments import ExperimentService
from app.services.models.training import FinetuneConfig
from app.tasks.training import run_finetune_task

router = APIRouter(prefix="/api/transfer", tags=["transfer"])


# ---------- Schemas ----------


class FinetuneRequest(BaseModel):
    backbone: str = "resnet18"
    dataset_path: str = ""
    num_epochs: int = 10
    learning_rate: float = 1e-3
    batch_size: int = 32
    freeze_layers: bool = True
    gradient_clip_value: float | None = None
    early_stopping_patience: int | None = None
    num_classes: int = 10
    experiment_name: str = "finetune-experiment"
    workspace_id: uuid.UUID = Field(...)
    model_id: uuid.UUID | None = None


class FinetuneResponse(BaseModel):
    job_id: str
    experiment_id: uuid.UUID
    status: str = "queued"


# ---------- Endpoints ----------


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_transfer(
    body: FinetuneRequest,
    db: AsyncSession = Depends(get_db),
) -> FinetuneResponse:
    """Start a fine-tuning job. Creates an experiment and queues a Celery task."""
    # Create the experiment record
    experiment = await ExperimentService.create_experiment(
        db,
        name=body.experiment_name,
        config={
            "backbone": body.backbone,
            "num_epochs": body.num_epochs,
            "learning_rate": body.learning_rate,
            "batch_size": body.batch_size,
            "freeze_layers": body.freeze_layers,
            "gradient_clip_value": body.gradient_clip_value,
            "early_stopping_patience": body.early_stopping_patience,
            "num_classes": body.num_classes,
        },
        model_id=body.model_id,
        workspace_id=body.workspace_id,
    )

    # Build the config dataclass for the worker
    config = FinetuneConfig(
        backbone=body.backbone,
        dataset_path=body.dataset_path,
        num_epochs=body.num_epochs,
        learning_rate=body.learning_rate,
        batch_size=body.batch_size,
        freeze_layers=body.freeze_layers,
        gradient_clip_value=body.gradient_clip_value,
        early_stopping_patience=body.early_stopping_patience,
        num_classes=body.num_classes,
    )

    # Queue Celery task
    task = run_finetune_task.delay(
        config_dict={
            "backbone": config.backbone,
            "dataset_path": config.dataset_path,
            "num_epochs": config.num_epochs,
            "learning_rate": config.learning_rate,
            "batch_size": config.batch_size,
            "freeze_layers": config.freeze_layers,
            "gradient_clip_value": config.gradient_clip_value,
            "early_stopping_patience": config.early_stopping_patience,
            "num_classes": config.num_classes,
        },
        experiment_id=str(experiment.id),
    )

    return FinetuneResponse(
        job_id=task.id,
        experiment_id=experiment.id,
        status="queued",
    )
