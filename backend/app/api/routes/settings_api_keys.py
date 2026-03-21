"""API key management routes — list, create, and revoke API keys."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.api_key import APIKey

router = APIRouter(prefix="/api/settings/api-keys", tags=["settings-api-keys"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

KEY_PREFIX = "vaf_prod_"


class APIKeyScope(BaseModel):
    module: str
    permissions: list[str]


class APIKeyCreate(BaseModel):
    name: str
    scopes: list[APIKeyScope]
    expires_in_days: Optional[int] = None


class APIKeyRead(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list[APIKeyScope]
    created_at: str
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class APIKeyCreated(BaseModel):
    """Returned once after creation — includes the full key."""

    id: str
    name: str
    key: str
    scopes: list[APIKeyScope]
    created_at: str
    expires_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_api_key() -> tuple[str, str, str]:
    """Return (full_key, prefix_display, sha256_hash)."""
    random_part = secrets.token_hex(24)
    full_key = f"{KEY_PREFIX}{random_part}"
    prefix_display = f"{KEY_PREFIX}{random_part[:6]}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix_display, key_hash


def _row_to_read(row: APIKey) -> APIKeyRead:
    return APIKeyRead(
        id=str(row.id),
        name=row.name,
        key_prefix=row.key_prefix,
        scopes=[APIKeyScope(**s) for s in (row.scopes or [])],
        created_at=row.created_at.isoformat() if row.created_at else "",
        expires_at=row.expires_at.isoformat() if row.expires_at else None,
        last_used_at=None,
        is_active=row.is_active,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[APIKeyRead])
async def list_api_keys(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
) -> list[APIKeyRead]:
    """List all API keys for a workspace (active only)."""
    result = await db.execute(
        select(APIKey)
        .where(APIKey.workspace_id == workspace_id, APIKey.is_active.is_(True))
        .order_by(APIKey.created_at.desc())
    )
    rows = result.scalars().all()
    return [_row_to_read(r) for r in rows]


@router.post("", response_model=APIKeyCreated, status_code=201)
async def create_api_key(
    body: APIKeyCreate,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
) -> APIKeyCreated:
    """Create a new API key. The full key is returned only once."""
    from datetime import timedelta

    full_key, prefix_display, key_hash = _generate_api_key()

    expires_at = None
    if body.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    new_key = APIKey(
        id=uuid4(),
        workspace_id=workspace_id,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),  # placeholder
        name=body.name,
        key_hash=key_hash,
        key_prefix=prefix_display,
        scopes=[s.model_dump() for s in body.scopes],
        expires_at=expires_at,
        is_active=True,
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    return APIKeyCreated(
        id=str(new_key.id),
        name=new_key.name,
        key=full_key,
        scopes=body.scopes,
        created_at=new_key.created_at.isoformat() if new_key.created_at else "",
        expires_at=new_key.expires_at.isoformat() if new_key.expires_at else None,
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Revoke (soft-delete) an API key."""
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.workspace_id == workspace_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.execute(
        update(APIKey).where(APIKey.id == key_id).values(is_active=False)
    )
    await db.commit()
