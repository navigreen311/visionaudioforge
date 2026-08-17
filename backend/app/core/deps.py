"""FastAPI dependencies: DB session, auth (JWT + API key), RBAC, tenancy."""

from typing import AsyncGenerator, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.identity import Identity
from app.core.security import decode_token
from app.database import async_session_factory
from app.models.user import User
from app.models.workspace import Workspace

security_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with async_session_factory() as session:
        yield session


def get_identity(request: Request) -> Identity | None:
    """Return the identity resolved by ``AuthenticationMiddleware``, if any.

    ``None`` means the request reached the handler without credentials — only
    possible on an allowlisted path or with ``AUTH_REQUIRED=False``.
    """
    return getattr(request.state, "identity", None)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via Bearer token or X-API-Key header.

    When ``AuthenticationMiddleware`` already resolved the caller, this reuses
    that result and only loads the ``User`` row — the token is not verified
    twice.
    """
    identity = get_identity(request)
    if identity is not None:
        result = await db.execute(select(User).where(User.id == identity.user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user

    # Check for API key in X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        from app.services.governance.api_keys import APIKeyService

        key_info = await APIKeyService.validate_key(db, api_key)
        if not key_info["valid"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )
        result = await db.execute(
            select(User).where(User.id == UUID(key_info["user_id"]))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key owner not found",
            )
        return user

    # Fall back to Bearer token
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication: provide Bearer token or X-API-Key header",
        )

    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_role(*roles: str) -> Callable:
    """Dependency factory: restrict access to users with specific roles.

    Usage: Depends(require_role("admin", "editor"))
    """

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized. Required: {', '.join(roles)}",
            )
        return current_user

    return _check_role


async def get_current_workspace(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    """Return the workspace the current user belongs to."""
    if current_user.workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has no associated workspace",
        )

    result = await db.execute(
        select(Workspace).where(Workspace.id == current_user.workspace_id)
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


# ---------------------------------------------------------------------------
# Tenancy — the single source of truth for "which workspace is this request?"
# ---------------------------------------------------------------------------
# Every route that reads or writes tenant-scoped data MUST take the workspace
# from here and never from a path/query parameter or request body. A caller who
# can name a workspace can name someone else's.
#
#     @router.get("/api/assets")
#     async def list_assets(
#         workspace_id: UUID = Depends(get_workspace_id),
#         db: AsyncSession = Depends(get_db),
#     ):
#         ...
#
# See docs/auth.md.


async def get_workspace_id(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """Return the workspace the caller is authenticated for.

    Order of resolution:

    1. ``request.state.workspace_id`` — put there by the middleware from the
       token's ``workspace_id`` claim. No I/O.
    2. The ``users.workspace_id`` column, for tokens minted before the claim
       existed. One indexed lookup, and only on routes that need a tenant.

    Fails closed: a caller with no resolvable workspace gets 403, never a
    default and never someone else's.
    """
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is not None:
        return workspace_id if isinstance(workspace_id, UUID) else UUID(str(workspace_id))

    identity = get_identity(request)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(User.workspace_id).where(User.id == identity.user_id)
    )
    resolved = result.scalar_one_or_none()
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user is not attached to a workspace",
        )

    # Memoise for the rest of the request.
    request.state.workspace_id = resolved
    return resolved


async def get_optional_workspace_id(request: Request) -> UUID | None:
    """Non-raising variant for endpoints that may legitimately be unscoped."""
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is None:
        return None
    return workspace_id if isinstance(workspace_id, UUID) else UUID(str(workspace_id))
