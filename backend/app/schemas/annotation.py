"""Pydantic schemas for annotation endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AnnotationCreate(BaseModel):
    asset_id: uuid.UUID
    annotation_type: str = Field(..., pattern="^(bbox|polygon|keypoint|segment|label|text)$")
    data: dict[str, Any]
    user_id: uuid.UUID
    dataset_id: Optional[uuid.UUID] = None


class AnnotationUpdate(BaseModel):
    data: dict[str, Any]


class AnnotationRead(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    dataset_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    annotation_type: str
    data: dict[str, Any]
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnnotationImport(BaseModel):
    data: dict[str, Any]
    format: str = "coco"


class AnnotationStatsResponse(BaseModel):
    total: int
    by_type: dict[str, int]
    by_label: dict[str, int]
    annotated_pct: float


class AnnotationExportResponse(BaseModel):
    """Flexible response for export data."""
    images: list[dict[str, Any]] | None = None
    annotations: list[dict[str, Any]] | None = None
    categories: list[dict[str, Any]] | None = None
    format: str | None = None
    classes: list[str] | None = None
    files: dict[str, str] | None = None
