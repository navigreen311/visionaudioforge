"""Asset management routes — upload, CRUD, download."""

from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from starlette.responses import Response

from app.core.deps import get_db
from app.schemas.asset import (
    AssetRead,
    AssetUpdate,
    AssetUploadResponse,
    BulkUploadResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.assets.asset_service import AssetService
from app.services.data.storage import MinIOStorageService

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _get_storage() -> MinIOStorageService:
    return MinIOStorageService()


# ------------------------------------------------------------------
# Upload (single or bulk)
# ------------------------------------------------------------------


@router.post("/upload", response_model=AssetUploadResponse | BulkUploadResponse)
async def upload_asset(
    file: list[UploadFile] = File(...),
    asset_type: str = Form(...),
    workspace_id: UUID = Form(...),
    tags: Optional[str] = Form(None),
    db=Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
):
    """Upload one or more files.

    ``tags`` is an optional JSON-encoded list of strings.
    When multiple files are provided the bulk-upload path is used.
    """
    parsed_tags: list[str] | None = json.loads(tags) if tags else None

    if len(file) == 1:
        asset = await AssetService.upload_asset(
            db=db,
            storage=storage,
            file=file[0],
            asset_type=asset_type,
            workspace_id=workspace_id,
            tags=parsed_tags,
        )
        return AssetUploadResponse.model_validate(asset)

    result = await AssetService.bulk_upload(
        db=db,
        storage=storage,
        files=file,
        workspace_id=workspace_id,
        asset_type=asset_type,
    )
    return BulkUploadResponse(
        uploaded=result["uploaded"],
        failed=result["failed"],
        assets=[AssetUploadResponse.model_validate(a) for a in result["assets"]],
    )


# ------------------------------------------------------------------
# List
# ------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse)
async def list_assets(
    workspace_id: UUID = Query(...),
    type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """List assets with optional type/tag filtering and pagination."""
    parsed_tags: list[str] | None = tags.split(",") if tags else None

    assets, total = await AssetService.list_assets(
        db=db,
        workspace_id=workspace_id,
        asset_type=type,
        tags=parsed_tags,
        skip=skip,
        limit=limit,
    )

    return PaginatedResponse(
        items=[AssetRead.model_validate(a) for a in assets],
        total=total,
        page=skip // limit,
        size=limit,
    )


# ------------------------------------------------------------------
# Read single
# ------------------------------------------------------------------


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: UUID, db=Depends(get_db)):
    """Retrieve a single asset with full metadata."""
    asset = await AssetService.get_asset(db, asset_id)
    return AssetRead.model_validate(asset)


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------


@router.put("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: UUID,
    body: AssetUpdate,
    db=Depends(get_db),
):
    """Update tags and/or metadata for an existing asset."""
    asset = await AssetService.update_asset(
        db=db,
        asset_id=asset_id,
        tags=body.tags,
        metadata=body.metadata_,
    )
    return AssetRead.model_validate(asset)


# ------------------------------------------------------------------
# Delete (soft)
# ------------------------------------------------------------------


@router.delete("/{asset_id}", response_model=AssetRead)
async def delete_asset(
    asset_id: UUID,
    db=Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
):
    """Soft-delete an asset (marks deleted in DB + removes from MinIO)."""
    asset = await AssetService.delete_asset(db, storage, asset_id)
    return AssetRead.model_validate(asset)


# ------------------------------------------------------------------
# Storage stats (stub)
# ------------------------------------------------------------------


@router.get("/storage-stats")
async def storage_stats():
    """Return storage usage breakdown (stub — replace with real query)."""
    return {
        "used_gb": 2.4,
        "total_gb": 50,
        "by_type": {
            "image": 1.2,
            "audio": 0.8,
            "video": 0.4,
        },
    }


# ------------------------------------------------------------------
# Download
# ------------------------------------------------------------------


@router.get("/{asset_id}/download")
async def download_asset(
    asset_id: UUID,
    db=Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
):
    """Stream the raw file back to the client."""
    data, filename, content_type = await AssetService.get_asset_file(db, storage, asset_id)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
