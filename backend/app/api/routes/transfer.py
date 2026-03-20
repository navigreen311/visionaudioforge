"""API routes for transfer learning / fine-tuning."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.models.cost_estimator import TrainingCostEstimator
from app.services.models.experiments import ExperimentService
from app.services.models.training import FinetuneConfig
from app.tasks.training import run_finetune_task

router = APIRouter(prefix="/api/transfer", tags=["transfer"])


# ---------- Schemas ----------


class LoRAConfigSchema(BaseModel):
    rank: int = 8
    alpha: float = 16.0
    target_modules: list[str] | None = None
    dropout: float = 0.1


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
    lora_config: LoRAConfigSchema | None = None
    quantize_after: bool = False
    gradient_accumulation_steps: int = 1


class FinetuneResponse(BaseModel):
    job_id: str
    experiment_id: uuid.UUID
    status: str = "queued"


class CostEstimateRequest(BaseModel):
    model_params: int = 11_000_000
    num_epochs: int = 10
    num_samples: int = 10_000
    gpu_type: str = "T4"


class QuantizeRequest(BaseModel):
    model_id: str
    dtype: str = "int8"


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
            "lora_config": body.lora_config.model_dump() if body.lora_config else None,
            "quantize_after": body.quantize_after,
            "gradient_accumulation_steps": body.gradient_accumulation_steps,
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
        lora_config=body.lora_config.model_dump() if body.lora_config else None,
        quantize_after=body.quantize_after,
        gradient_accumulation_steps=body.gradient_accumulation_steps,
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
            "lora_config": config.lora_config,
            "quantize_after": config.quantize_after,
            "gradient_accumulation_steps": config.gradient_accumulation_steps,
        },
        experiment_id=str(experiment.id),
    )

    return FinetuneResponse(
        job_id=task.id,
        experiment_id=experiment.id,
        status="queued",
    )


@router.post("/estimate-cost")
async def estimate_cost(body: CostEstimateRequest) -> dict[str, Any]:
    """Estimate training cost for a given configuration."""
    estimator = TrainingCostEstimator()
    return estimator.estimate_cost(body.model_dump())


@router.post("/quantize")
async def quantize_model(body: QuantizeRequest) -> dict[str, Any]:
    """Quantize a model (stub — returns size reduction estimate).

    In production this would load the model from the registry, quantize it,
    and save the quantized version.  V1 returns an estimate only.
    """
    from app.services.models.quantization import ModelQuantizer

    quantizer = ModelQuantizer()
    # Without a real model loaded, return a size-reduction estimate
    # Assume ~11M params for resnet18 as default
    estimate = quantizer.estimate_size_reduction(
        original_params=11_000_000, dtype=body.dtype
    )
    return {
        "model_id": body.model_id,
        "dtype": body.dtype,
        "status": "estimated",
        **estimate,
    }


@router.get("/instance-recommendation")
async def instance_recommendation(
    model_params: int = Query(default=11_000_000),
    batch_size: int = Query(default=32),
) -> dict[str, Any]:
    """Recommend a GPU instance for the given model size and batch size."""
    estimator = TrainingCostEstimator()
    return estimator.recommend_instance(model_params, batch_size)
