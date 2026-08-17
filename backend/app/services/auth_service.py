"""Authentication service: register, login, refresh, user lookups."""

import re
from typing import Any
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


def access_token_claims(user: User) -> dict[str, Any]:
    """Claims for an access token: who, and which tenant.

    Embedding ``workspace_id`` makes tenant resolution I/O-free — the auth
    middleware reads it straight off the signed token instead of querying the
    users table on every request. See ``docs/auth.md``.

    Omitted rather than sent as null when the user has no workspace, so
    ``get_workspace_id`` falls through to its lookup and then fails closed,
    instead of a "null" string reaching a UUID parser.

    The claim is a snapshot: reassigning a user to a different workspace takes
    effect on their next access token, i.e. within the 30-minute expiry. That
    is the usual JWT trade — no read on the hot path, bounded staleness. If a
    reassignment ever needs to be immediate, revoke the session rather than
    reintroducing a per-request lookup.
    """
    claims: dict[str, Any] = {"sub": str(user.id)}
    if user.workspace_id is not None:
        claims["workspace_id"] = str(user.workspace_id)
    return claims


def refresh_token_claims(user: User) -> dict[str, Any]:
    """Claims for a refresh token: identity only.

    Deliberately *not* tenant-scoped. A refresh token lives for 7 days, and
    baking a workspace into it would let a stale tenant survive a week. The
    workspace is re-read from the user row each time an access token is minted.
    """
    return {"sub": str(user.id)}


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

        return {
            "access_token": create_access_token(access_token_claims(user)),
            "refresh_token": create_refresh_token(refresh_token_claims(user)),
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

        return {
            "access_token": create_access_token(access_token_claims(user)),
            "refresh_token": create_refresh_token(refresh_token_claims(user)),
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

        # Re-read the workspace from the user row rather than trusting the
        # refresh token: this is the point at which a reassignment lands.
        return {
            "access_token": create_access_token(access_token_claims(user)),
        }
