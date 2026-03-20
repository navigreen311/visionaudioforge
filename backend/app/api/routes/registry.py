"""API routes for the Model Registry."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
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
    db: AsyncSession = Depends(get_db),
):
    record = await svc.register_model(
        db,
        name=body.name,
        version=body.version,
        backbone=body.backbone,
        metrics=body.metrics,
        workspace_id=body.workspace_id,
    )
    return record


@router.get("/models")
async def list_models(
    workspace_id: UUID = Query(...),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    items, total = await svc.list_models(db, workspace_id, model_status=status, skip=skip, limit=limit)
    total_pages = (total + limit - 1) // limit if limit else 1
    return PaginatedResponse(
        items=[ModelRead.model_validate(i) for i in items],
        total=total,
        page=skip // limit + 1 if limit else 1,
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
