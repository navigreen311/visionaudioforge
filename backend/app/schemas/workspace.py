from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


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
    # The workspaces table has had a plan column all along; leaving it out of
    # the update schema meant a plan change could not be sent at all.
    plan: Optional[str] = None
    settings: Optional[dict] = None


class WorkspaceStats(BaseModel):
    members: int
    models: int
    datasets: int
    assets: int
    pipelines: int


class WorkspaceDetail(WorkspaceRead):
    """Workspace with embedded stats."""
    stats: WorkspaceStats


class MemberRead(BaseModel):
    id: UUID
    email: str
    role: str

    model_config = {"from_attributes": True}


class MemberInvite(BaseModel):
    email: EmailStr
    role: str = "viewer"


class MemberRoleUpdate(BaseModel):
    role: str
