"""Schemas for settings/users RBAC endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class WorkspaceUserResponse(BaseModel):
    """User row for the settings Users tab."""

    id: UUID
    name: str
    email: str
    role: str
    status: str  # active | pending | inactive
    avatar_url: str | None = None
    last_active: str | None = None

    model_config = {"from_attributes": True}


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"


class InviteUserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    status: str
    invited_at: datetime
    # Whether the invitation actually reached a mail provider. The invite used
    # to report success unconditionally while sending nothing at all, so the
    # console could not tell "invited" from "row created, no email".
    email_sent: bool = False
    email_note: str | None = None


class UpdateRoleRequest(BaseModel):
    role: str


class UpdateRoleResponse(BaseModel):
    id: UUID
    role: str
    updated_at: datetime
