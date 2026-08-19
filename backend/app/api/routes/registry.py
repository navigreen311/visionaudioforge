"""API routes for the Model Registry."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from app.core.deps import get_optional_workspace_id
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.deps import get_db, get_workspace_id
from app.models.model_registry import ModelRecord, ModelStatus
from app.models.workspace import SYSTEM_WORKSPACE_ID
from app.schemas.common import PaginatedResponse
from app.schemas.registry import (
    CompareRequest,
    ModelCreate,
    ModelRead,
    RollbackRequest,
    StatusUpdate,
)
from app.services.models import ModelRegistryService

router = APIRouter(prefix="/api/registry", tags=["registry"])
svc = ModelRegistryService()


@router.post("/register", response_model=ModelRead, status_code=201)
async def register_model(
    body: ModelCreate,
    caller_workspace: UUID | None = Depends(get_optional_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = body.workspace_id or caller_workspace or SYSTEM_WORKSPACE_ID

    try:
        record = await svc.register_model(
            db,
            name=body.name,
            version=body.version,
            backbone=body.backbone,
            metrics=body.metrics,
            workspace_id=workspace_id,
            tags=body.tags,
            description=body.description,
            status=body.status,
        )
    except IntegrityError:
        # Almost always a workspace_id that does not exist. Say so, rather
        # than letting a database constraint surface as an unhandled 500.
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"workspace_id {workspace_id} does not exist",
        )

    return record


@router.get("/models")
async def list_models(
    # Optional so the endpoint answers unscoped callers the way the other
    # list endpoints do. An unresolvable workspace yields an empty page,
    # never an unscoped read across tenants.
    workspace_id: UUID | None = Query(None),
    caller_workspace: UUID | None = Depends(get_optional_workspace_id),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = workspace_id or caller_workspace
    if workspace_id is None:
        return PaginatedResponse(
            items=[], total=0, page=1, size=limit, page_size=limit, total_pages=1
        )

    try:
        items, total = await svc.list_models(db, workspace_id, model_status=status, skip=skip, limit=limit)
        validated_items = [ModelRead.model_validate(i) for i in items]
    except Exception:
        # Fallback to empty list when DB schema is out of sync
        validated_items = []
        total = 0
    total_pages = (total + limit - 1) // limit if limit else 1
    return PaginatedResponse(
        items=validated_items,
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        page_size=limit,
        total_pages=total_pages,
    )


@router.get("/models/{model_id}", response_model=ModelRead)
async def get_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_model(db, model_id)


@router.put("/models/{model_id}/status", response_model=ModelRead)
async def update_model_status(
    model_id: UUID,
    body: StatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.update_status(db, model_id, body.status)


@router.post("/compare")
async def compare_models(
    body: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    return await svc.compare_models(db, body.model_a_id, body.model_b_id)


@router.post("/models/{model_id}/rollback", response_model=ModelRead)
async def rollback_model(
    model_id: UUID,
    body: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    return await svc.rollback(db, model_id, body.to_version)


# ------------------------------------------------------------------
# Available models for federation (lightweight list, no DB required)
# ------------------------------------------------------------------

@router.get("/models/available")
async def list_available_models(
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, str]]:
    """Models in this workspace that a federated round can train against.

    This returned the same five invented entries - ResNet-50, YOLOv8, CLIP,
    Wav2Vec2, EfficientNet - to every workspace, whether or not it had ever
    registered a model. Picking one started a federation against a model id that
    did not exist.
    """
    rows = (
        await db.execute(
            select(ModelRecord)
            .where(
                ModelRecord.workspace_id == session_workspace,
                ModelRecord.status.in_(
                    (ModelStatus.registered, ModelStatus.staging, ModelStatus.production)
                ),
            )
            .order_by(ModelRecord.updated_at.desc())
        )
    ).scalars().all()

    return [
        {
            "id": str(m.id),
            "name": m.name,
            "version": m.version or "",
            "backbone": m.backbone or "",
        }
        for m in rows
    ]


# ------------------------------------------------------------------
# Model Card attachment stub
# ------------------------------------------------------------------

class ModelCardPayload(BaseModel):
    """Model card data attached to a registry model. Mirrors frontend schema."""
    modelName: str = ""
    version: str = ""
    modelType: str = ""
    architecture: str = ""
    trainingDate: str = ""
    framework: str = ""
    license: str = ""
    primaryUseCases: str = ""
    outOfScope: str = ""
    targetUsers: str = ""
    metrics: list[dict] = Field(default_factory=list)
    knownLimitations: str = ""
    ethicalConsiderations: str = ""
    biasFairness: str = ""
    datasetName: str = ""
    datasetSize: str = ""
    datasetDescription: str = ""
    preprocessingSteps: str = ""


@router.patch("/models/{model_id}/model-card")
async def attach_model_card(
    model_id: UUID,
    body: ModelCardPayload,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    """Attach a model card to a registered model.

    This used to validate the payload, echo it back claiming it had been
    saved, and throw it away - so a card written by a compliance reviewer
    vanished on reload while the UI said it was stored.

    Stored on the model's `metrics` JSON column under `model_card`, which needs
    no migration.
    """
    model = (
        await db.execute(
            select(ModelRecord).where(
                ModelRecord.id == model_id,
                ModelRecord.workspace_id == session_workspace,
            )
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")

    card = body.model_dump()
    merged = dict(model.metrics or {})
    merged["model_card"] = card
    model.metrics = merged
    # A JSON column mutated in place is not seen by the unit of work.
    flag_modified(model, "metrics")
    await db.commit()

    return {"model_id": str(model_id), "saved": True, "model_card": card}


