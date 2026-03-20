"""Authentication service: register, login, refresh, user lookups."""

import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.models.workspace import Workspace


def _slugify(name: str) -> str:
    """Convert a workspace name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class AuthService:
    """Handles authentication logic: registration, login, token refresh."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def register(
        self, email: str, password: str, workspace_name: str
    ) -> dict:
        """Create a new User and Workspace, return access + refresh tokens."""
        existing = await self.get_user_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # Create user first (workspace needs owner_id)
        user = User(
            email=email,
            hashed_password=hash_password(password),
            role="admin",
        )
        self.db.add(user)
        await self.db.flush()  # populate user.id

        # Create workspace owned by this user
        workspace = Workspace(
            name=workspace_name,
            slug=_slugify(workspace_name),
            owner_id=user.id,
        )
        self.db.add(workspace)
        await self.db.flush()

        # Link user to workspace
        user.workspace_id = workspace.id
        await self.db.commit()
        await self.db.refresh(user)

        token_data = {"sub": str(user.id)}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
            "user": user,
        }

    async def login(self, email: str, password: str) -> dict:
        """Verify credentials and return tokens."""
        user = await self.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        token_data = {"sub": str(user.id)}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
            "user": user,
        }

    async def refresh(self, refresh_token: str) -> dict:
        """Validate a refresh token and issue a new access token."""
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is not a refresh token",
            )

        user = await self.get_user_by_id(UUID(payload["sub"]))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return {
            "access_token": create_access_token({"sub": str(user.id)}),
        }
