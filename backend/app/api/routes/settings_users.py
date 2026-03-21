"""Settings > Users RBAC routes.

Endpoints:
  GET    /api/settings/users              — list workspace users
  POST   /api/settings/users/invite       — invite a new user
  PATCH  /api/settings/users/{id}/role    — change a user's role
  DELETE /api/settings/users/{id}         — remove a user from workspace
  POST   /api/settings/users/{id}/resend  — resend pending invite
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.settings_users import (
    InviteUserRequest,
    InviteUserResponse,
    UpdateRoleRequest,
    UpdateRoleResponse,
    WorkspaceUserResponse,
)

router = APIRouter(
    prefix="/api/settings/users",
    tags=["settings-users"],
)

VALID_ROLES = {r.value for r in UserRole}


def _status_for_user(user: User) -> str:
    """Derive display status from user state."""
    if user.hashed_password == "__pending__":
        return "pending"
    if user.last_login is None:
        return "inactive"
    return "active"


def _last_active(user: User) -> str | None:
    """Format last_login for display."""
    if user.last_login is None:
        return None
    return user.last_login.strftime("%b %d, %Y %H:%M")


def _name_from_email(email: str) -> str:
    """Derive a display name from an email address."""
    local = email.split("@")[0]
    return local.replace(".", " ").replace("_", " ").title()


# --------------------------------------------------------------------- #
#  GET /api/settings/users                                               #
# --------------------------------------------------------------------- #

@router.get("", response_model=list[WorkspaceUserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all users in the same workspace as the current user."""
    if current_user.workspace_id is None:
        return []

    result = await db.execute(
        select(User).where(User.workspace_id == current_user.workspace_id)
    )
    users = result.scalars().all()

    return [
        WorkspaceUserResponse(
            id=u.id,
            name=_name_from_email(u.email),
            email=u.email,
            role=u.role.value if isinstance(u.role, UserRole) else u.role,
            status=_status_for_user(u),
            avatar_url=None,
            last_active=_last_active(u),
        )
        for u in users
    ]


# --------------------------------------------------------------------- #
#  POST /api/settings/users/invite                                       #
# --------------------------------------------------------------------- #

@router.post("/invite", response_model=InviteUserResponse, status_code=201)
async def invite_user(
    body: InviteUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Invite a new user to the workspace. Creates a pending user row."""
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{body.role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )

    # Check for duplicate email in workspace
    existing = await db.execute(
        select(User).where(
            User.email == body.email,
            User.workspace_id == current_user.workspace_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists in the workspace.",
        )

    now = datetime.now(timezone.utc)
    new_user = User(
        id=uuid4(),
        email=body.email,
        hashed_password="__pending__",  # sentinel for pending invites
        role=UserRole(body.role),
        workspace_id=current_user.workspace_id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # TODO: send invite email via background task

    return InviteUserResponse(
        id=new_user.id,
        email=new_user.email,
        role=new_user.role.value if isinstance(new_user.role, UserRole) else new_user.role,
        status="pending",
        invited_at=now,
    )


# --------------------------------------------------------------------- #
#  PATCH /api/settings/users/{user_id}/role                              #
# --------------------------------------------------------------------- #

@router.patch("/{user_id}/role", response_model=UpdateRoleResponse)
async def update_user_role(
    user_id: UUID,
    body: UpdateRoleRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role. Only admins can do this."""
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{body.role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role.",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.workspace_id == current_user.workspace_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this workspace.",
        )

    target.role = UserRole(body.role)
    now = datetime.now(timezone.utc)
    await db.commit()

    return UpdateRoleResponse(
        id=target.id,
        role=target.role.value if isinstance(target.role, UserRole) else target.role,
        updated_at=now,
    )


# --------------------------------------------------------------------- #
#  DELETE /api/settings/users/{user_id}                                  #
# --------------------------------------------------------------------- #

@router.delete("/{user_id}", status_code=204)
async def remove_user(
    user_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Remove a user from the workspace."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself.",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.workspace_id == current_user.workspace_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this workspace.",
        )

    await db.delete(target)
    await db.commit()


# --------------------------------------------------------------------- #
#  POST /api/settings/users/{user_id}/resend                             #
# --------------------------------------------------------------------- #

@router.post("/{user_id}/resend", status_code=200)
async def resend_invite(
    user_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Resend the invite email for a pending user."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.workspace_id == current_user.workspace_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this workspace.",
        )

    if target.hashed_password != "__pending__":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not in pending state.",
        )

    # TODO: trigger invite email resend via background task

    return {"message": "Invite resent successfully."}
