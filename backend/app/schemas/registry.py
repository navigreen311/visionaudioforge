"""Pydantic schemas for the Model Registry API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=50)
    backbone: str | None = None
    metrics: dict | None = None
    workspace_id: UUID


class ModelRead(BaseModel):
    id: UUID
    name: str
    version: str
    status: str
    backbone: str | None
    metrics: dict | None
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    status: str


class CompareRequest(BaseModel):
    model_a_id: UUID
    model_b_id: UUID


class RollbackRequest(BaseModel):
    to_version: str
