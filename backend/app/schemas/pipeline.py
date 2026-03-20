from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class PipelineCreate(BaseModel):
    name: str
    definition: dict[str, Any]


class PipelineRead(BaseModel):
    id: UUID
    name: str
    version: str
    definition: dict[str, Any]
    status: str
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PipelineRunRead(BaseModel):
    id: UUID
    pipeline_id: UUID
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    results: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}
