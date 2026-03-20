from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class DatasetCreate(BaseModel):
    name: str
    modality: str


class DatasetRead(BaseModel):
    id: UUID
    name: str
    modality: str
    version: str
    stats: dict[str, Any]
    workspace_id: UUID
    sample_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetStats(BaseModel):
    total_samples: int
    modality_breakdown: dict[str, int]
    version: str
