from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class ModelCreate(BaseModel):
    name: str
    version: str
    backbone: Optional[str] = None
    metrics: Optional[dict[str, Any]] = None


class ModelRead(BaseModel):
    id: UUID
    name: str
    version: str
    status: str
    backbone: Optional[str] = None
    metrics: dict[str, Any]
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelUpdate(BaseModel):
    status: Optional[str] = None
    metrics: Optional[dict[str, Any]] = None


class ModelCompare(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_ids: list[UUID]
