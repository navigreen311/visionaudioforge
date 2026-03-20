"""Workspace management routes: CRUD, members, roles, stats."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.schemas.workspace import (
    MemberInvite,
    MemberRead,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceDetail,
    WorkspaceRead,
    WorkspaceStats,
    WorkspaceUpdate,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List workspaces the current user belongs to."""
    if current_user.workspace_id is None:
        return []
    svc = WorkspaceService(db)
    workspace = await svc.get_workspace(current_user.workspace_id)
    return [workspace]


@router.post("", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workspace owned by the current user."""
    svc = WorkspaceService(db)
    workspace = await svc.create_workspace(
        name=body.name,
        owner_id=current_user.id,
    )
    # Link current user to the new workspace as admin
    current_user.workspace_id = workspace.id
    current_user.role = "admin"
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceDetail)
async def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get workspace details including stats."""
    svc = WorkspaceService(db)
    workspace = await svc.get_workspace(workspace_id)
    stats = await svc.get_workspace_stats(workspace_id)
    return WorkspaceDetail(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        plan=workspace.plan.value if hasattr(workspace.plan, "value") else workspace.plan,
        created_at=workspace.created_at,
        stats=WorkspaceStats(**stats),
    )


@router.put("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: UUID,
    body: WorkspaceUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update workspace name or settings (admin only)."""
    svc = WorkspaceService(db)
    workspace = await svc.update_workspace(
        workspace_id=workspace_id,
        name=body.name,
        settings=body.settings,
    )
    await db.commit()
    await db.refresh(workspace)
    return workspace


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get("/{workspace_id}/members", response_model=list[MemberRead])
async def list_members(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members of the workspace."""
    svc = WorkspaceService(db)
    members = await svc.list_workspace_members(workspace_id)
    return members


@router.post("/{workspace_id}/members", response_model=MemberRead, status_code=201)
async def invite_member(
    workspace_id: UUID,
    body: MemberInvite,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Invite a member to the workspace (admin only)."""
    svc = WorkspaceService(db)
    user = await svc.invite_member(
        workspace_id=workspace_id,
        email=body.email,
        role=body.role,
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{workspace_id}/members/{user_id}", response_model=MemberRead)
async def update_member_role(
    workspace_id: UUID,
    user_id: UUID,
    body: MemberRoleUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Change a member's role (admin only)."""
    svc = WorkspaceService(db)
    user = await svc.update_member_role(
        workspace_id=workspace_id,
        user_id=user_id,
        new_role=body.role,
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
async def remove_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the workspace (admin only)."""
    svc = WorkspaceService(db)
    await svc.remove_member(workspace_id=workspace_id, user_id=user_id)
    await db.commit()
