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
    # As with datasets, the workspace may arrive as a query parameter.
    workspace_id: uuid.UUID | None = None


class PipelineValidate(BaseModel):
    definition: dict[str, Any]


# -- Response bodies -------------------------------------------------------

class PipelineRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    version: str = "1.0"
    definition: dict[str, Any]
    # The pipelines table carries a status; omitting it here hid the
    # draft/active distinction from every caller.
    status: str = "draft"
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PipelineRunRead(BaseModel):
    """Mirrors the pipeline_runs table.

    That table carries started_at/finished_at and a `results` blob, and does
    not use the timestamp mixin — so created_at/updated_at were fields the
    model could never populate.
    """

    id: uuid.UUID
    pipeline_id: uuid.UUID
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    results: dict[str, Any] | None = None
    error: str | None = None

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
