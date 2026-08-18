"""ChainOfCustodyService — audit trail for evidence access and integrity.

Custody records and integrity baselines are rows, not process memory. The
previous implementation appended to a module-level list and *tried* to mirror
the row into audit_logs inside a bare ``except`` — so a failed write was
swallowed, and the chain was read back from memory regardless. Both failure
modes produce the same outcome: an evidence trail that reports a clean,
complete history it cannot actually substantiate.

Writes here are allowed to raise. A custody event that cannot be recorded must
fail loudly, because the alternative is an access nobody can later prove
happened.
"""

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.evidence import AssetIntegrity, CustodyAction, CustodyEvent
from app.models.user import User

logger = logging.getLogger(__name__)

# Valid custody actions
VALID_ACTIONS = {action.value for action in CustodyAction}

_HASH_CHUNK_BYTES = 8192


def _as_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _hash_file(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_BYTES), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


class ChainOfCustodyService:
    """Tracks access to evidence assets and verifies integrity."""

    @staticmethod
    async def log_access(
        db: AsyncSession,
        asset_id: str,
        user_id: str,
        action: str,
        details: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Record an access event against a custody-tracked asset.

        Raises:
            ValueError: If ``action`` is not a recognised custody action.
        """
        if action not in VALID_ACTIONS:
            raise ValueError(
                f"Invalid custody action '{action}'. "
                f"Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
            )

        workspace = _as_uuid(workspace_id)
        now = datetime.now(timezone.utc)

        # The actor is always recorded as text. user_id is only set when it
        # resolves to a real user, so an unknown or deleted account cannot
        # make the custody write fail — losing the record would be worse than
        # losing the foreign key.
        user_uuid = await ChainOfCustodyService._known_user(db, user_id)

        event = CustodyEvent(
            id=uuid.uuid4(),
            workspace_id=workspace,
            asset_id=str(asset_id),
            user_id=user_uuid,
            actor=str(user_id) if user_id else None,
            action=CustodyAction(action),
            details=details,
            timestamp=now,
        )
        db.add(event)

        # The workspace-wide audit log gets the same event. It is a mirror for
        # operators, not the source of truth. It used to be written only when
        # the workspace was known, because audit_logs.workspace_id was NOT NULL;
        # that dropped custody events rather than storing them unattributed,
        # which is the wrong trade for a chain of custody. Since revision 017 the
        # column is nullable, so the event is always recorded.
        db.add(
            AuditLog(
                id=uuid.uuid4(),
                user_id=user_uuid,
                action=f"custody.{action}",
                resource=f"asset:{asset_id}",
                payload={"details": details, "asset_id": str(asset_id)},
                workspace_id=workspace,
            )
        )

        await db.commit()

        logger.info(
            "Custody log: user=%s action=%s asset=%s", user_id, action, asset_id
        )
        return {
            "id": str(event.id),
            "asset_id": event.asset_id,
            "user_id": str(user_id) if user_id else None,
            "action": action,
            "details": details,
            "timestamp": now.isoformat(),
        }

    @staticmethod
    async def _known_user(db: AsyncSession, user_id: Any) -> Optional[uuid.UUID]:
        """Return the user id only if that user actually exists."""
        candidate = _as_uuid(user_id)
        if candidate is None:
            return None

        result = await db.execute(select(User.id).where(User.id == candidate))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_custody_chain(
        db: AsyncSession,
        asset_id: str,
    ) -> list[dict[str, Any]]:
        """Return an asset's full chain of custody, oldest first."""
        result = await db.execute(
            select(CustodyEvent)
            .where(CustodyEvent.asset_id == str(asset_id))
            .order_by(CustodyEvent.timestamp, CustodyEvent.id)
        )
        return [
            {
                "timestamp": _iso(event.timestamp),
                "user": event.actor or (str(event.user_id) if event.user_id else None),
                "action": event.action.value,
                "details": event.details,
            }
            for event in result.scalars().all()
        ]

    @staticmethod
    async def verify_integrity(
        db: AsyncSession,
        asset_id: str,
        original_hash: Optional[str] = None,
        file_path: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Compare an asset's current SHA-256 against its recorded baseline.

        The first successful hash for an asset becomes its baseline; every
        later check compares against that stored row.
        """
        current_hash: Optional[str] = None

        if file_path:
            if not os.path.exists(file_path):
                return {
                    "intact": False,
                    "hash": None,
                    "note": f"File not found at {file_path}",
                }
            current_hash = _hash_file(file_path)

        stored = await ChainOfCustodyService._get_baseline(db, asset_id)
        stored_hash = stored.sha256 if stored else None

        if original_hash and current_hash:
            intact = current_hash == original_hash
            note = (
                "Hash matches original"
                if intact
                else "Hash mismatch — file may have been modified"
            )
        elif stored_hash and current_hash:
            intact = current_hash == stored_hash
            note = (
                "Hash matches stored record"
                if intact
                else "Hash mismatch — file may have been modified"
            )
        elif current_hash:
            await ChainOfCustodyService.store_hash(
                db, asset_id, current_hash, workspace_id=workspace_id
            )
            intact = True
            note = "Initial hash recorded"
        else:
            intact = True
            note = "No file path provided; integrity check skipped"

        return {"intact": intact, "hash": current_hash, "note": note}

    @staticmethod
    async def _get_baseline(
        db: AsyncSession, asset_id: str
    ) -> Optional[AssetIntegrity]:
        result = await db.execute(
            select(AssetIntegrity).where(AssetIntegrity.asset_id == str(asset_id))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def generate_custody_report(
        db: AsyncSession,
        asset_id: str,
    ) -> dict[str, Any]:
        """Full custody report: chain, integrity, access count, unique users."""
        chain = await ChainOfCustodyService.get_custody_chain(db, asset_id)
        integrity = await ChainOfCustodyService.verify_integrity(db, asset_id)

        unique_users = {entry["user"] for entry in chain if entry.get("user")}

        return {
            "asset_id": str(asset_id),
            "chain": chain,
            "integrity": integrity,
            "access_count": len(chain),
            "unique_users": len(unique_users),
        }

    @staticmethod
    async def store_hash(
        db: AsyncSession,
        asset_id: str,
        hash_value: str,
        workspace_id: Optional[str] = None,
    ) -> None:
        """Record (or replace) the known-good hash for an asset."""
        existing = await ChainOfCustodyService._get_baseline(db, asset_id)
        if existing is not None:
            existing.sha256 = hash_value
            existing.recorded_at = datetime.now(timezone.utc)
        else:
            db.add(
                AssetIntegrity(
                    id=uuid.uuid4(),
                    workspace_id=_as_uuid(workspace_id),
                    asset_id=str(asset_id),
                    sha256=hash_value,
                )
            )
        await db.commit()
