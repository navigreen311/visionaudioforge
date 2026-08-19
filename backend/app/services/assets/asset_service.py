"""Asset management service — upload, CRUD, and MinIO storage integration."""

from __future__ import annotations

import logging
import hashlib
import mimetypes
import uuid
from typing import Any, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.services.data.storage import MinIOStorageService

logger = logging.getLogger(__name__)

BUCKET = "vaf-assets"


class AssetService:
    """Stateless service encapsulating all asset operations."""

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    @staticmethod
    async def upload_asset(
        db: AsyncSession,
        storage: MinIOStorageService,
        file: UploadFile,
        asset_type: str,
        workspace_id: uuid.UUID,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Asset:
        """Upload a single file to MinIO and persist an Asset record."""
        file_bytes = await file.read()
        size_bytes = len(file_bytes)
        # Content hash, recorded so duplicate detection can be a real lookup
        # rather than the `{"duplicate": false}` it always used to return. Stored
        # in the metadata JSON so this needs no migration; indexed lookups can
        # come later if the table grows enough to want one.
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        filename = file.filename or "untitled"
        content_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

        object_key = f"{workspace_id}/{asset_type}/{uuid.uuid4()}_{filename}"

        path = await storage.upload_file(
            bucket=BUCKET,
            key=object_key,
            file_data=file_bytes,
            content_type=content_type,
        )

        asset = Asset(
            type=AssetType(asset_type),
            path=path,
            filename=filename,
            size_bytes=size_bytes,
            metadata_={**(metadata or {}), "sha256": content_hash},
            tags=tags,
            workspace_id=workspace_id,
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        logger.info("Created asset %s (%s, %d bytes)", asset.id, filename, size_bytes)
        return asset

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    @staticmethod
    async def list_assets(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        asset_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Asset], int]:
        """Return a paginated, optionally filtered list of assets."""
        base = select(Asset).where(
            Asset.workspace_id == workspace_id,
            Asset.metadata_["deleted"].as_boolean().is_not(True),
        )

        if asset_type:
            base = base.where(Asset.type == AssetType(asset_type))

        if tags:
            base = base.where(Asset.tags.overlap(tags))

        # Total count (without pagination)
        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        # Paginated rows
        rows_q = base.order_by(Asset.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(rows_q)
        assets = list(result.scalars().all())

        return assets, total

    # ------------------------------------------------------------------
    # Single read
    # ------------------------------------------------------------------

    @staticmethod
    async def get_asset(db: AsyncSession, asset_id: uuid.UUID) -> Asset:
        """Fetch a single asset or raise 404."""
        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalar_one_or_none()
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        return asset

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    @staticmethod
    async def update_asset(
        db: AsyncSession,
        asset_id: uuid.UUID,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Asset:
        """Update mutable fields (tags, metadata) on an existing asset."""
        asset = await AssetService.get_asset(db, asset_id)
        if tags is not None:
            asset.tags = tags
        if metadata is not None:
            asset.metadata_ = metadata
        await db.commit()
        await db.refresh(asset)
        return asset

    # ------------------------------------------------------------------
    # Delete (soft)
    # ------------------------------------------------------------------

    @staticmethod
    async def delete_asset(
        db: AsyncSession,
        storage: MinIOStorageService,
        asset_id: uuid.UUID,
    ) -> Asset:
        """Soft-delete: mark metadata.deleted=true and remove from MinIO."""
        asset = await AssetService.get_asset(db, asset_id)

        # Remove the physical object from MinIO
        path = asset.path  # e.g. "vaf-assets/ws/type/uuid_file"
        parts = path.split("/", 1)
        bucket = parts[0] if len(parts) == 2 else BUCKET
        key = parts[1] if len(parts) == 2 else path
        await storage.delete_file(bucket, key)

        # Soft-delete in DB
        meta = dict(asset.metadata_) if asset.metadata_ else {}
        meta["deleted"] = True
        asset.metadata_ = meta
        await db.commit()
        await db.refresh(asset)
        logger.info("Soft-deleted asset %s", asset_id)
        return asset

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    @staticmethod
    async def get_asset_file(
        db: AsyncSession,
        storage: MinIOStorageService,
        asset_id: uuid.UUID,
    ) -> tuple[bytes, str, str]:
        """Return (bytes, filename, content_type) for streaming back."""
        asset = await AssetService.get_asset(db, asset_id)

        path = asset.path
        parts = path.split("/", 1)
        bucket = parts[0] if len(parts) == 2 else BUCKET
        key = parts[1] if len(parts) == 2 else path

        data = await storage.download_file(bucket, key)
        content_type = mimetypes.guess_type(asset.filename)[0] or "application/octet-stream"
        return data, asset.filename, content_type

    # ------------------------------------------------------------------
    # Bulk upload
    # ------------------------------------------------------------------

    @staticmethod
    async def bulk_upload(
        db: AsyncSession,
        storage: MinIOStorageService,
        files: list[UploadFile],
        workspace_id: uuid.UUID,
        asset_type: str,
    ) -> dict[str, Any]:
        """Upload multiple files, returning summary stats."""
        uploaded = 0
        failed = 0
        assets: list[Asset] = []

        for file in files:
            try:
                asset = await AssetService.upload_asset(
                    db=db,
                    storage=storage,
                    file=file,
                    asset_type=asset_type,
                    workspace_id=workspace_id,
                )
                assets.append(asset)
                uploaded += 1
            except Exception:
                logger.exception("Failed to upload %s", file.filename)
                failed += 1

        return {"uploaded": uploaded, "failed": failed, "assets": assets}
