"""API key management: create, validate, list, revoke, rotate."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey

VALID_SCOPES = [
    "read", "write", "admin", "vision", "audio",
    "search", "pipeline", "agents",
]


def _generate_key() -> str:
    """Generate a new API key with the 'vaf_' prefix."""
    return "vaf_" + secrets.token_urlsafe(32)


def _hash_key(key: str) -> str:
    """SHA-256 hash an API key for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def _key_prefix(key: str) -> str:
    """Return the visible prefix of a key (first 12 chars)."""
    return key[:12] + "..."


class APIKeyService:
    """Manage API keys for workspace programmatic access."""

    @staticmethod
    async def create_key(
        db: AsyncSession,
        workspace_id: str | UUID,
        user_id: str | UUID,
        name: str,
        scopes: list[str],
        expires_in_days: int | None = None,
    ) -> dict[str, Any]:
        """Create a new API key. The full key is returned only once."""
        # Validate scopes
        for scope in scopes:
            if scope not in VALID_SCOPES:
                raise ValueError(f"Invalid scope: {scope}. Valid: {VALID_SCOPES}")

        raw_key = _generate_key()
        hashed = _hash_key(raw_key)
        prefix = _key_prefix(raw_key)
        key_id = uuid4()

        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            id=key_id,
            workspace_id=UUID(str(workspace_id)),
            user_id=UUID(str(user_id)),
            name=name,
            key_hash=hashed,
            key_prefix=prefix,
            scopes=scopes,
            expires_at=expires_at,
            is_active=True,
        )
        db.add(api_key)
        await db.commit()

        return {
            "key": raw_key,
            "key_prefix": prefix,
            "key_id": str(key_id),
            "scopes": scopes,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

    @staticmethod
    async def validate_key(
        db: AsyncSession,
        key: str,
    ) -> dict[str, Any]:
        """Validate an API key by hashing and looking it up."""
        hashed = _hash_key(key)
        result = await db.execute(
            select(APIKey).where(
                APIKey.key_hash == hashed,
                APIKey.is_active.is_(True),
            )
        )
        api_key = result.scalar_one_or_none()

        if api_key is None:
            return {"valid": False, "workspace_id": None, "scopes": [], "user_id": None}

        # Check expiry
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return {"valid": False, "workspace_id": None, "scopes": [], "user_id": None}

        return {
            "valid": True,
            "workspace_id": str(api_key.workspace_id),
            "scopes": api_key.scopes or [],
            "user_id": str(api_key.user_id),
        }

    @staticmethod
    async def list_keys(
        db: AsyncSession,
        workspace_id: str | UUID,
    ) -> list[dict[str, Any]]:
        """List all active API keys for a workspace (prefix only)."""
        result = await db.execute(
            select(APIKey).where(
                APIKey.workspace_id == UUID(str(workspace_id)),
                APIKey.is_active.is_(True),
            )
        )
        keys = result.scalars().all()
        return [
            {
                "key_id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes or [],
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            }
            for k in keys
        ]

    @staticmethod
    async def revoke_key(
        db: AsyncSession,
        key_id: str | UUID,
    ) -> bool:
        """Revoke an API key by setting is_active=False."""
        result = await db.execute(
            update(APIKey)
            .where(APIKey.id == UUID(str(key_id)))
            .values(is_active=False)
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def rotate_key(
        db: AsyncSession,
        key_id: str | UUID,
    ) -> dict[str, Any]:
        """Revoke the old key and create a new one with the same scopes."""
        # Fetch old key
        result = await db.execute(
            select(APIKey).where(APIKey.id == UUID(str(key_id)))
        )
        old_key = result.scalar_one_or_none()
        if old_key is None:
            raise ValueError("API key not found")

        # Revoke old
        old_key.is_active = False
        await db.commit()

        # Create new with same scopes
        return await APIKeyService.create_key(
            db,
            workspace_id=old_key.workspace_id,
            user_id=old_key.user_id,
            name=old_key.name,
            scopes=old_key.scopes or [],
            expires_in_days=None,
        )
