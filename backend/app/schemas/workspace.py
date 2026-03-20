from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceRead(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    settings: Optional[dict] = None
