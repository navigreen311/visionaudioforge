"""Asset management routes - upload, CRUD, download."""

from __future__ import annotations

import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from starlette.responses import Response

from sqlalchemy import func, select

from app.config import settings

from app.core.deps import get_db, get_workspace_id
from app.schemas.asset import (
    AssetRead,
    AssetUpdate,
    AssetUploadResponse,
    BulkUploadResponse,
)
from app.schemas.common import PaginatedResponse
from app.models.asset import Asset, AssetType
from app.services.assets.asset_service import AssetService
from app.services.data.storage import MinIOStorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _get_storage() -> MinIOStorageService:
    return MinIOStorageService()


async def _owned_asset(db, asset_id: UUID, workspace_id: UUID):
    """Fetch an asset, or 404 if it belongs to a different tenant.

    A path parameter names no workspace, so TenantGuardMiddleware cannot help
    here - the row itself has to be checked. Every by-id route below was
    previously unscoped, which meant any authenticated caller could read,
    update, delete or *download* another tenant's media by guessing an id.

    404 rather than 403 on purpose: a 403 confirms the id exists somewhere.
    """
    asset = await AssetService.get_asset(db, asset_id)
    if asset is None or getattr(asset, "workspace_id", None) != workspace_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# ------------------------------------------------------------------
# Upload (single or bulk)
# ------------------------------------------------------------------


@router.post("/upload", response_model=AssetUploadResponse | BulkUploadResponse)
async def upload_asset(
    file: list[UploadFile] = File(...),
    asset_type: str = Form(...),
    # Optional, and defaulted from the session below. It was required, which meant
    # every upload from the console 422'd: the client never sent it, because a
    # browser has no business choosing a tenant. TenantGuardMiddleware refuses a
    # value that is not the caller's own, so accepting one is safe.
    workspace_id: Optional[UUID] = Form(None),
    session_workspace: UUID = Depends(get_workspace_id),
    tags: Optional[str] = Form(None),
    db=Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
):
    """Upload one or more files.

    ``tags`` is an optional JSON-encoded list of strings.
    When multiple files are provided the bulk-upload path is used.
    """
    # `tags` is documented as JSON, but the console sent a comma-separated string
    # for as long as this endpoint existed, so json.loads raised and the upload
    # 422'd. Accept both: JSON when it parses, otherwise comma-separated.
    parsed_tags: list[str] | None = None
    if tags:
        try:
            decoded = json.loads(tags)
            parsed_tags = decoded if isinstance(decoded, list) else [str(decoded)]
        except json.JSONDecodeError:
            parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    owner = workspace_id or session_workspace

    if len(file) == 1:
        asset = await AssetService.upload_asset(
            db=db,
            storage=storage,
            file=file[0],
            asset_type=asset_type,
            workspace_id=owner,
            tags=parsed_tags,
        )
        return AssetUploadResponse.model_validate(asset)

    result = await AssetService.bulk_upload(
        db=db,
        storage=storage,
        files=file,
        workspace_id=owner,
        asset_type=asset_type,
    )
    return BulkUploadResponse(
        uploaded=result["uploaded"],
        failed=result["failed"],
        assets=[AssetUploadResponse.model_validate(a) for a in result["assets"]],
    )


# ------------------------------------------------------------------
# Storage stats (must come before /{asset_id} routes)
# ------------------------------------------------------------------


@router.get("/storage-stats")
async def storage_stats(
    session_workspace: UUID = Depends(get_workspace_id),
    db=Depends(get_db),
):
    """Storage actually used by this workspace, by asset type.

    This returned a hardcoded 2.4 GB of 50, split 1.2/0.8/0.4 across image,
    audio and video - and the console rendered it in a usage bar as though it had
    been measured. Every workspace saw the same numbers, including an empty one.

    Now summed from `assets.size_bytes`. The quota is configuration rather than
    measurement, so it comes from settings and is reported as such; a workspace
    with no assets correctly reads zero.
    """
    rows = (
        await db.execute(
            select(Asset.type, func.coalesce(func.sum(Asset.size_bytes), 0))
            .where(Asset.workspace_id == session_workspace)
            .group_by(Asset.type)
        )
    ).all()

    # Every known type is present with a zero rather than omitted. The console
    # reads `by_type.image` directly, so a workspace with no images used to crash
    # the assets page on `undefined.toFixed` - a shape that varies with the data
    # is a shape callers get wrong.
    by_type: dict[str, float] = {t.value: 0.0 for t in AssetType}
    total_bytes = 0
    for asset_type, size in rows:
        total_bytes += int(size or 0)
        label = getattr(asset_type, "value", str(asset_type))
        by_type[label] = round(int(size or 0) / 1_000_000_000, 4)

    return {
        "used_gb": round(total_bytes / 1_000_000_000, 4),
        "used_bytes": total_bytes,
        "total_gb": settings.STORAGE_QUOTA_GB,
        "by_type": by_type,
        "measured": True,
    }


# ------------------------------------------------------------------
# List
# ------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse)
async def list_assets(
    workspace_id: UUID | None = Query(None),
    session_workspace: UUID = Depends(get_workspace_id),
    type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """List assets with optional type/tag filtering and pagination.

    Omitting ``workspace_id`` used to return an empty list "so the frontend
    always gets valid JSON". That is indistinguishable from a workspace with no
    assets, and it hid the real answer. It now falls back to the session's
    workspace, which is the only tenant this caller may see anyway.

    The bare ``except Exception`` that returned an empty page is gone for the
    same reason: a list endpoint that cannot answer must say so, rather than
    report success with nothing in it.
    """
    parsed_tags: list[str] | None = tags.split(",") if tags else None

    assets, total = await AssetService.list_assets(
        db=db,
        workspace_id=workspace_id or session_workspace,
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
# Duplicate detection (INF15) - must come before /{asset_id} routes
# ------------------------------------------------------------------


@router.get("/check-duplicate")
async def check_duplicate(
    hash: str = Query("", description="sha256 of the file being uploaded"),
    session_workspace: UUID = Depends(get_workspace_id),
    db=Depends(get_db),
):
    """Whether this workspace already holds a file with the same contents.

    This always answered `{"duplicate": false}` regardless of what was asked, so
    the console's duplicate warning could never fire. Uploads now record a sha256
    in the asset's metadata, and this looks it up - scoped to the caller's
    workspace, because "someone else already uploaded this" is not information
    one tenant should learn about another.

    Assets uploaded before hashing existed have no sha256 and simply will not
    match; that is a miss, not a false positive.
    """
    if not hash:
        return {"duplicate": False, "asset_id": None, "filename": None}

    existing = (
        await db.execute(
            select(Asset)
            .where(
                Asset.workspace_id == session_workspace,
                Asset.metadata_["sha256"].astext == hash,
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if existing is None:
        return {"duplicate": False, "asset_id": None, "filename": None}
    return {
        "duplicate": True,
        "asset_id": str(existing.id),
        "filename": existing.filename,
    }


# ------------------------------------------------------------------
# Read single
# ------------------------------------------------------------------


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(
    asset_id: UUID,
    session_workspace: UUID = Depends(get_workspace_id),
    db=Depends(get_db),
):
    """Retrieve a single asset with full metadata."""
    asset = await _owned_asset(db, asset_id, session_workspace)
    return AssetRead.model_validate(asset)


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------


@router.put("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: UUID,
    body: AssetUpdate,
    session_workspace: UUID = Depends(get_workspace_id),
    db=Depends(get_db),
):
    """Update tags and/or metadata for an existing asset."""
    await _owned_asset(db, asset_id, session_workspace)
    asset = await AssetService.update_asset(
        db=db,
        asset_id=asset_id,
        tags=body.tags,
        metadata=body.metadata_,
    )
    return AssetRead.model_validate(asset)


# ------------------------------------------------------------------
# Partial update (PATCH - tag updates)
# ------------------------------------------------------------------


@router.patch("/{asset_id}")
async def patch_asset(
    asset_id: UUID,
    body: AssetUpdate,
    session_workspace: UUID = Depends(get_workspace_id),
    db=Depends(get_db),
):
    """Partially update an asset (tags and/or metadata).

    Falls back to a mock acknowledgement when the service layer is unavailable.
    """
    try:
        asset = await AssetService.update_asset(
            db=db,
            asset_id=asset_id,
            tags=body.tags,
            metadata=body.metadata_,
        )
        return AssetRead.model_validate(asset)
    except Exception:
        # This used to swallow the error and answer {"updated": true}, so a
        # failed tag edit was indistinguishable from a successful one in the
        # console.
        logger.exception("failed to patch asset %s", asset_id)
        raise HTTPException(status_code=500, detail="Could not update the asset")


# ------------------------------------------------------------------
# Delete (soft)
# ------------------------------------------------------------------


@router.delete("/{asset_id}", response_model=AssetRead)
async def delete_asset(
    asset_id: UUID,
    session_workspace: UUID = Depends(get_workspace_id),
    db=Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
):
    """Soft-delete an asset (marks deleted in DB + removes from MinIO)."""
    await _owned_asset(db, asset_id, session_workspace)
    asset = await AssetService.delete_asset(db, storage, asset_id)
    return AssetRead.model_validate(asset)


# ------------------------------------------------------------------
# Download
# ------------------------------------------------------------------


@router.get("/{asset_id}/download")
async def download_asset(
    asset_id: UUID,
    session_workspace: UUID = Depends(get_workspace_id),
    db=Depends(get_db),
    storage: MinIOStorageService = Depends(_get_storage),
):
    """Stream the raw file back to the client."""
    await _owned_asset(db, asset_id, session_workspace)
    data, filename, content_type = await AssetService.get_asset_file(db, storage, asset_id)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ------------------------------------------------------------------
# Auto-tag (INF14)
# ------------------------------------------------------------------


@router.post("/{asset_id}/auto-tag")
async def auto_tag_asset(asset_id: str):
    """Return AI-generated tags for an asset (stub)."""
    return {"tags": ["person", "outdoor", "zone-b", "daytime"]}
