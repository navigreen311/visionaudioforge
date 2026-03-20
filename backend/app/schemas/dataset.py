"""Pydantic schemas for dataset endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    modality: str = Field(..., pattern="^(image|video|audio|multimodal)$")
    workspace_id: uuid.UUID


class DatasetRead(BaseModel):
    id: uuid.UUID
    name: str
    modality: str
    description: str | None = None
    sample_count: int = 0
    size_bytes: int = 0
    version: int = 1
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
