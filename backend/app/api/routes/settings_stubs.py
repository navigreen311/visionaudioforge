"""Settings API stubs — workspace config, API keys, and user management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Path
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class WorkspaceLimits(BaseModel):
    streams: int = 2
    storage_gb: int = 10
    api_calls: int = 10000
    team_members: int = 3


class WorkspaceUsage(BaseModel):
    streams: int = 0
    storage_gb: float = 2.4
    api_calls: int = 1240
    team_members: int = 1


class WorkspaceResponse(BaseModel):
    name: str = "My Workspace"
    description: str = "Default workspace for VisionAudioForge"
    plan: str = "free"
    limits: WorkspaceLimits = WorkspaceLimits()
    usage: WorkspaceUsage = WorkspaceUsage()
    created_at: str = "2025-06-15T10:30:00Z"
    region: str = "US East"


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ApiKeyItem(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    created_at: str
    last_used: str | None = None
    expires: str | None = None


class ApiKeyCreate(BaseModel):
    name: str = "New Key"
    scopes: list[str] = ["read"]
    expires_in_days: int | None = 90


class ApiKeyCreated(BaseModel):
    id: str
    name: str
    key: str
    prefix: str
    scopes: list[str]
    created_at: str
    expires: str | None = None
    message: str = "Store this key securely — it will not be shown again."


class UserItem(BaseModel):
    id: str
    email: str
    name: str
    role: str
    avatar: str | None = None
    joined_at: str
    last_active: str | None = None


class InviteRequest(BaseModel):
    email: str
    role: str = "viewer"


class RoleUpdate(BaseModel):
    role: str


# ---------------------------------------------------------------------------
# In-memory mock state
# ---------------------------------------------------------------------------

_workspace = WorkspaceResponse()

_mock_keys: list[dict] = [
    {
        "id": "key-001",
        "name": "Production API",
        "prefix": "vaf_prod_",
        "scopes": ["read", "write", "admin"],
        "created_at": "2025-08-01T09:00:00Z",
        "last_used": "2026-03-20T14:22:00Z",
        "expires": "2026-08-01T09:00:00Z",
    },
    {
        "id": "key-002",
        "name": "CI/CD Pipeline",
        "prefix": "vaf_ci_",
        "scopes": ["read", "write"],
        "created_at": "2025-10-12T11:30:00Z",
        "last_used": "2026-03-19T08:15:00Z",
        "expires": "2026-04-12T11:30:00Z",
    },
    {
        "id": "key-003",
        "name": "Read-Only Dashboard",
        "prefix": "vaf_ro_",
        "scopes": ["read"],
        "created_at": "2026-01-05T16:45:00Z",
        "last_used": None,
        "expires": None,
    },
]

_mock_users: list[dict] = [
    {
        "id": "usr-001",
        "email": "alice@example.com",
        "name": "Alice Chen",
        "role": "owner",
        "avatar": None,
        "joined_at": "2025-06-15T10:30:00Z",
        "last_active": "2026-03-21T09:00:00Z",
    },
    {
        "id": "usr-002",
        "email": "bob@example.com",
        "name": "Bob Martinez",
        "role": "admin",
        "avatar": None,
        "joined_at": "2025-07-20T14:00:00Z",
        "last_active": "2026-03-20T17:45:00Z",
    },
    {
        "id": "usr-003",
        "email": "carol@example.com",
        "name": "Carol Kim",
        "role": "editor",
        "avatar": None,
        "joined_at": "2025-09-10T08:15:00Z",
        "last_active": "2026-03-18T12:30:00Z",
    },
    {
        "id": "usr-004",
        "email": "dave@example.com",
        "name": "Dave Okonkwo",
        "role": "viewer",
        "avatar": None,
        "joined_at": "2026-01-03T11:00:00Z",
        "last_active": "2026-03-15T10:00:00Z",
    },
]


# ---------------------------------------------------------------------------
# Workspace routes
# ---------------------------------------------------------------------------

@router.get("/workspace", response_model=WorkspaceResponse)
async def get_workspace():
    """Return current workspace settings."""
    return _workspace


@router.patch("/workspace", response_model=WorkspaceResponse)
async def update_workspace(body: WorkspaceUpdate):
    """Partially update workspace settings."""
    global _workspace
    data = _workspace.model_dump()
    updates = body.model_dump(exclude_unset=True)
    data.update(updates)
    _workspace = WorkspaceResponse(**data)
    return _workspace


@router.post("/logo")
async def upload_logo():
    """Stub for workspace logo upload."""
    return {"status": "success", "message": "Logo updated successfully."}


@router.post("/export")
async def export_settings():
    """Export workspace settings as plain text."""
    lines = [
        "# VisionAudioForge — Workspace Export",
        f"name: {_workspace.name}",
        f"description: {_workspace.description}",
        f"plan: {_workspace.plan}",
        f"region: {_workspace.region}",
        f"created_at: {_workspace.created_at}",
        f"streams_used: {_workspace.usage.streams}/{_workspace.limits.streams}",
        f"storage_used: {_workspace.usage.storage_gb}/{_workspace.limits.storage_gb} GB",
        f"api_calls_used: {_workspace.usage.api_calls}/{_workspace.limits.api_calls}",
        f"team_members: {_workspace.usage.team_members}/{_workspace.limits.team_members}",
    ]
    return PlainTextResponse("\n".join(lines), media_type="text/plain")


@router.delete("/workspace")
async def delete_workspace():
    """Stub for workspace deletion."""
    return {"status": "success", "message": "Workspace scheduled for deletion."}


# ---------------------------------------------------------------------------
# API Keys routes
# ---------------------------------------------------------------------------

@router.get("/api-keys", response_model=list[ApiKeyItem])
async def list_api_keys():
    """Return all API keys (masked)."""
    return [ApiKeyItem(**k) for k in _mock_keys]


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(body: ApiKeyCreate):
    """Create a new API key — returns the full key once."""
    now = datetime.now(timezone.utc).isoformat()
    key_id = f"key-{uuid.uuid4().hex[:8]}"
    prefix = "vaf_new_"
    full_key = f"{prefix}{uuid.uuid4().hex}"

    expires = None
    if body.expires_in_days:
        from datetime import timedelta
        expires = (datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)).isoformat()

    new_entry = {
        "id": key_id,
        "name": body.name,
        "prefix": prefix,
        "scopes": body.scopes,
        "created_at": now,
        "last_used": None,
        "expires": expires,
    }
    _mock_keys.append(new_entry)

    return ApiKeyCreated(
        id=key_id,
        name=body.name,
        key=full_key,
        prefix=prefix,
        scopes=body.scopes,
        created_at=now,
        expires=expires,
    )


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str = Path(..., description="API key ID")):
    """Revoke an API key."""
    return {"status": "success", "message": f"API key {key_id} revoked."}


# ---------------------------------------------------------------------------
# Users routes
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserItem])
async def list_users():
    """Return workspace team members."""
    return [UserItem(**u) for u in _mock_users]


@router.post("/users/invite", status_code=201)
async def invite_user(body: InviteRequest):
    """Invite a user to the workspace."""
    return {
        "status": "success",
        "message": f"Invitation sent to {body.email} as {body.role}.",
    }


@router.patch("/users/{user_id}/role")
async def update_user_role(
    body: RoleUpdate,
    user_id: str = Path(..., description="User ID"),
):
    """Update a team member's role."""
    return {
        "status": "success",
        "message": f"User {user_id} role updated to {body.role}.",
    }


@router.delete("/users/{user_id}")
async def remove_user(user_id: str = Path(..., description="User ID")):
    """Remove a user from the workspace."""
    return {"status": "success", "message": f"User {user_id} removed."}
