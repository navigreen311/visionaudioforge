"""Pydantic schemas for Pipeline API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# -- Request bodies --------------------------------------------------------

class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    definition: dict[str, Any] = Field(..., description="Pipeline graph definition (nodes + edges)")
    workspace_id: uuid.UUID


class PipelineValidate(BaseModel):
    definition: dict[str, Any]


# -- Response bodies -------------------------------------------------------

class PipelineRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    definition: dict[str, Any]
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PipelineRunRead(BaseModel):
    id: uuid.UUID
    pipeline_id: uuid.UUID
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PipelineRunStart(BaseModel):
    run_id: uuid.UUID
    status: str = "pending"


class NodeTypeInfo(BaseModel):
    type: str
    category: str
    description: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str]
