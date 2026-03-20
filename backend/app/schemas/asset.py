from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class AssetCreate(BaseModel):
    type: str
    path: str
    filename: str
    size_bytes: Optional[int] = None
    tags: Optional[list[str]] = None


class AssetRead(BaseModel):
    id: UUID
    type: str
    path: str
    filename: str
    size_bytes: Optional[int] = None
    metadata_: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetUploadResponse(BaseModel):
    id: UUID
    type: str
    filename: str
    size_bytes: Optional[int] = None
    tags: Optional[list[str]] = None
    workspace_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetUpdate(BaseModel):
    tags: Optional[list[str]] = None
    metadata_: Optional[dict[str, Any]] = None


class AssetFilter(BaseModel):
    type: Optional[str] = None
    tags: Optional[list[str]] = None
    workspace_id: Optional[UUID] = None


class BulkUploadResponse(BaseModel):
    uploaded: int
    failed: int
    assets: list[AssetUploadResponse]
