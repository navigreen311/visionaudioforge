"""Workspace management service: CRUD, members, roles, and stats."""

import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.asset import Asset
from app.models.dataset import Dataset
from app.models.model_registry import ModelRecord
from app.models.pipeline import Pipeline
from app.models.user import User, UserRole
from app.models.workspace import Workspace


def _slugify(name: str) -> str:
    """Convert a workspace name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class WorkspaceService:
    """Manages workspace lifecycle, membership, and statistics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_workspace(
        self,
        name: str,
        owner_id: UUID,
        plan: str = "free",
    ) -> Workspace:
        """Create a new workspace with an auto-generated unique slug."""
        base_slug = _slugify(name)
        slug = base_slug
        suffix = 0

        # Ensure slug uniqueness
        while True:
            result = await self.db.execute(
                select(Workspace).where(Workspace.slug == slug)
            )
            if result.scalar_one_or_none() is None:
                break
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        workspace = Workspace(
            name=name,
            slug=slug,
            owner_id=owner_id,
            plan=plan,
            settings={},
        )
        self.db.add(workspace)
        await self.db.flush()
        await self.db.refresh(workspace)
        return workspace

    async def get_workspace(self, workspace_id: UUID) -> Workspace:
        """Fetch a workspace by ID or raise 404."""
        result = await self.db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
        return workspace

    async def update_workspace(
        self,
        workspace_id: UUID,
        name: str | None = None,
        settings: dict | None = None,
    ) -> Workspace:
        """Update workspace name and/or settings."""
        workspace = await self.get_workspace(workspace_id)
        if name is not None:
            workspace.name = name
        if settings is not None:
            workspace.settings = settings
        await self.db.flush()
        await self.db.refresh(workspace)
        return workspace

    async def list_workspace_members(self, workspace_id: UUID) -> list[User]:
        """Return all users belonging to the workspace."""
        # Verify workspace exists
        await self.get_workspace(workspace_id)
        result = await self.db.execute(
            select(User).where(User.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def invite_member(
        self,
        workspace_id: UUID,
        email: str,
        role: str = "viewer",
    ) -> User:
        """Invite a member to the workspace. Creates the user if not found."""
        # Verify workspace exists
        await self.get_workspace(workspace_id)

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            # Create a new user with a placeholder password
            user = User(
                email=email,
                hashed_password=hash_password("changeme-invite"),
                role=role,
                workspace_id=workspace_id,
            )
            self.db.add(user)
        else:
            if user.workspace_id == workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User is already a member of this workspace",
                )
            user.workspace_id = workspace_id
            user.role = role

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def remove_member(self, workspace_id: UUID, user_id: UUID) -> None:
        """Remove a member from the workspace."""
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.workspace_id == workspace_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this workspace",
            )
        user.workspace_id = None
        await self.db.flush()

    async def update_member_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
        new_role: str,
    ) -> User:
        """Change a member's role within the workspace."""
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.workspace_id == workspace_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this workspace",
            )

        # Validate role
        valid_roles = {r.value for r in UserRole}
        if new_role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid role '{new_role}'. Must be one of: {', '.join(sorted(valid_roles))}",
            )

        user.role = new_role
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_workspace_stats(self, workspace_id: UUID) -> dict:
        """Return counts of members, models, datasets, assets, and pipelines."""
        # Verify workspace exists
        await self.get_workspace(workspace_id)

        members = await self.db.execute(
            select(func.count()).select_from(User).where(
                User.workspace_id == workspace_id
            )
        )
        models = await self.db.execute(
            select(func.count()).select_from(ModelRecord).where(
                ModelRecord.workspace_id == workspace_id
            )
        )
        datasets = await self.db.execute(
            select(func.count()).select_from(Dataset).where(
                Dataset.workspace_id == workspace_id
            )
        )
        assets = await self.db.execute(
            select(func.count()).select_from(Asset).where(
                Asset.workspace_id == workspace_id
            )
        )
        pipelines = await self.db.execute(
            select(func.count()).select_from(Pipeline).where(
                Pipeline.workspace_id == workspace_id
            )
        )

        return {
            "members": members.scalar_one(),
            "models": models.scalar_one(),
            "datasets": datasets.scalar_one(),
            "assets": assets.scalar_one(),
            "pipelines": pipelines.scalar_one(),
        }
