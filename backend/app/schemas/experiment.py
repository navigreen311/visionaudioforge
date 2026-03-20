from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class ExperimentCreate(BaseModel):
    model_config = {"protected_namespaces": ()}
    name: str
    config: dict[str, Any]
    model_id: Optional[UUID] = None


class ExperimentRead(BaseModel):
    id: UUID
    name: str
    config: dict[str, Any]
    status: str
    best_epoch: Optional[dict[str, Any]] = None
    model_id: Optional[UUID] = None
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class EpochLog(BaseModel):
    epoch: int
    metrics: dict[str, Any]
