"""API routes for transfer learning / fine-tuning."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.models.automl import TRAINING_RECIPES, AutoMLService
from app.services.models.continuous_learning import ContinuousLearningService
from app.services.models.experiments import ExperimentService
from app.services.models.fewshot import FewShotClassifier
from app.services.models.training import FinetuneConfig
from app.services.models.zeroshot import ZeroShotClassifier
from app.tasks.training import run_finetune_task

router = APIRouter(prefix="/api/transfer", tags=["transfer"])

# Singleton service instances
_continuous_learning = ContinuousLearningService()
_few_shot = FewShotClassifier()
_zero_shot: ZeroShotClassifier | None = None


def _get_zero_shot() -> ZeroShotClassifier:
    global _zero_shot
    if _zero_shot is None:
        _zero_shot = ZeroShotClassifier()
    return _zero_shot


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


# ---------- AutoML Schemas ----------


class SweepRequest(BaseModel):
    base_config: dict[str, Any] = {}
    param_grid: dict[str, list[Any]] = {}
    num_trials: int = 10


class BackboneRequest(BaseModel):
    dataset_stats: dict[str, Any]


class FeedbackRequest(BaseModel):
    model_id: str
    predicted: str
    corrected: str
    input_data: Any = None
    user_id: str | None = None


class ZeroShotRequest(BaseModel):
    candidate_labels: list[str]


class FewShotBuildRequest(BaseModel):
    examples: dict[str, list[str]]  # class_name → list of base64-encoded images


# ---------- AutoML Endpoints ----------


@router.post("/automl/sweep")
async def automl_sweep(body: SweepRequest) -> dict[str, Any]:
    """Run a hyperparameter grid search."""
    results = AutoMLService.hyperparameter_sweep(
        base_config=body.base_config,
        param_grid=body.param_grid,
        num_trials=body.num_trials,
    )
    return {"results": results}


@router.post("/automl/recommend-backbone")
async def recommend_backbone(body: BackboneRequest) -> dict[str, Any]:
    """Recommend a backbone architecture based on dataset statistics."""
    return AutoMLService.recommend_backbone(body.dataset_stats)


@router.get("/recipes")
async def list_recipes() -> dict[str, Any]:
    """List all available training recipe presets."""
    return {"recipes": list(TRAINING_RECIPES.keys()), "details": TRAINING_RECIPES}


@router.get("/recipes/{use_case}")
async def get_recipe(use_case: str) -> dict[str, Any]:
    """Get a specific training recipe by use-case name."""
    return AutoMLService.training_recipe(use_case)


# ---------- Few-shot Endpoints ----------


@router.post("/few-shot/build")
async def few_shot_build(body: FewShotBuildRequest) -> dict[str, Any]:
    """Build a few-shot classifier from base64-encoded example images."""
    import base64

    import numpy as np

    examples: dict[str, list[np.ndarray]] = {}
    for cls_name, b64_list in body.examples.items():
        images: list[np.ndarray] = []
        for b64_str in b64_list:
            raw = base64.b64decode(b64_str)
            arr = np.frombuffer(raw, dtype=np.uint8)
            images.append(arr)
        examples[cls_name] = images

    result = _few_shot.build_classifier(examples)
    return result


@router.post("/few-shot/predict")
async def few_shot_predict(
    file: UploadFile = File(...),
    classifier_id: str = "",
) -> dict[str, Any]:
    """Predict class for an uploaded image using few-shot centroids."""
    import numpy as np

    contents = await file.read()
    arr = np.frombuffer(contents, dtype=np.uint8)
    # In production, centroids would be loaded from a store by classifier_id.
    # For now return a placeholder.
    return {"note": "classifier_id lookup not yet implemented", "classifier_id": classifier_id}


@router.post("/zero-shot")
async def zero_shot_classify(body: ZeroShotRequest, file: UploadFile = File(...)) -> dict[str, Any]:
    """Zero-shot classify an uploaded image against candidate labels."""
    import numpy as np

    contents = await file.read()
    arr = np.frombuffer(contents, dtype=np.uint8)
    zs = _get_zero_shot()
    return zs.classify(arr, body.candidate_labels)


# ---------- Feedback / Continuous Learning Endpoints ----------


@router.post("/feedback")
async def capture_feedback(body: FeedbackRequest) -> dict[str, Any]:
    """Store a prediction feedback / correction event."""
    event = _continuous_learning.capture_feedback(
        model_id=body.model_id,
        input_data=body.input_data,
        predicted=body.predicted,
        corrected=body.corrected,
        user_id=body.user_id,
    )
    return event


@router.get("/feedback/{model_id}")
async def feedback_queue(model_id: str) -> dict[str, Any]:
    """Get the feedback queue status for a model."""
    return _continuous_learning.get_feedback_queue(model_id)
