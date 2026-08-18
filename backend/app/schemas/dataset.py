"""Pydantic schemas for dataset endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    modality: str = Field(..., pattern="^(image|video|audio|multimodal)$")
    # Optional in the body: most endpoints here take workspace_id as a query
    # parameter. The route requires one from either source and rejects a
    # request that supplies neither.
    workspace_id: uuid.UUID | None = None


class DatasetSplitInfo(BaseModel):
    train: int = 0
    val: int = 0
    test: int = 0


class DatasetRead(BaseModel):
    id: uuid.UUID
    name: str
    modality: str
    description: str | None = None
    sample_count: int = 0
    size_bytes: int = 0
    version: int = 1
    # These two were each declared twice; the second, weaker declaration won
    # and rejected the DatasetSplitInfo the route actually builds.
    split: DatasetSplitInfo = Field(default_factory=DatasetSplitInfo)
    class_counts: dict[str, int] = Field(default_factory=dict)
    stats: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DatasetStats(BaseModel):
    total_samples: int = 0
    modality_breakdown: dict[str, int] = {}
    total_size_bytes: int = 0
    label_distribution: dict[str, int] = {}


class SplitRequest(BaseModel):
    train: float = Field(0.7, ge=0, le=1)
    val: float = Field(0.15, ge=0, le=1)
    test: float = Field(0.15, ge=0, le=1)
    stratified: bool = True


class SplitResponse(BaseModel):
    train: int
    val: int
    test: int


class UploadSummary(BaseModel):
    uploaded: int
    failed: int
    errors: list[str] = []
