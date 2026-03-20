"""ChainOfCustodyService — audit trail for evidence access and integrity."""

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Valid custody actions
VALID_ACTIONS = {"viewed", "downloaded", "exported", "modified", "shared", "deleted"}

# In-memory custody log for V1 (production would use AuditLog table)
_custody_logs: list[dict[str, Any]] = []

# Hash cache for integrity verification
_hash_store: dict[str, str] = {}


class ChainOfCustodyService:
    """Tracks access to evidence assets and verifies integrity."""

    @staticmethod
    async def log_access(
        db: Any,
        asset_id: str,
        user_id: str,
        action: str,
        details: Optional[str] = None,
    ) -> dict[str, Any]:
        """Log an access event for a custody-tracked asset.

        Args:
            db: Database session.
            asset_id: The asset being accessed.
            user_id: Who is accessing it.
            action: One of 'viewed', 'downloaded', 'exported', 'modified',
                    'shared', 'deleted'.
            details: Optional free-text details.

        Returns:
            The created audit log record dict.

        Raises:
            ValueError: If action is not in the valid set.
        """
        if action not in VALID_ACTIONS:
            raise ValueError(
                f"Invalid custody action '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
            )

        record = {
            "id": str(uuid.uuid4()),
            "asset_id": asset_id,
            "user_id": user_id,
            "action": action,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        _custody_logs.append(record)

        # Also attempt to write to DB AuditLog table
        try:
            from app.models.audit_log import AuditLog

            log_entry = AuditLog(
                user_id=uuid.UUID(user_id) if user_id else None,
                action=f"custody.{action}",
                resource=f"asset:{asset_id}",
                payload={"details": details, "asset_id": asset_id},
                workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            )
            db.add(log_entry)
            await db.commit()
        except Exception:
            logger.debug("Could not persist custody log to DB, using in-memory store")

        logger.info(
            "Custody log: user=%s action=%s asset=%s",
            user_id, action, asset_id,
        )
        return record

    @staticmethod
    async def get_custody_chain(
        db: Any,
        asset_id: str,
    ) -> list[dict[str, Any]]:
        """Get the full chain of custody for an asset, ordered chronologically.

        Returns:
            List of custody records with timestamp, user, action, details.
        """
        chain = [
            {
                "timestamp": log["timestamp"],
                "user": log["user_id"],
                "action": log["action"],
                "details": log.get("details"),
            }
            for log in _custody_logs
            if log["asset_id"] == asset_id
        ]
        # Sort chronologically
        chain.sort(key=lambda x: x["timestamp"])
        return chain

    @staticmethod
    async def verify_integrity(
        db: Any,
        asset_id: str,
        original_hash: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Verify integrity of an asset by computing and comparing SHA-256 hash.

        Args:
            db: Database session.
            asset_id: The asset to verify.
            original_hash: Known-good hash to compare against.
            file_path: Path to the asset file on disk.

        Returns:
            Dict with intact (bool), hash (str), note (str).
        """
        current_hash: Optional[str] = None

        # Compute hash from file if path provided
        if file_path and os.path.exists(file_path):
            sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            current_hash = sha256.hexdigest()
        elif file_path:
            return {
                "intact": False,
                "hash": None,
                "note": f"File not found at {file_path}",
            }

        # Use stored hash if no file
        stored_hash = _hash_store.get(asset_id)

        if original_hash and current_hash:
            intact = current_hash == original_hash
            note = "Hash matches original" if intact else "Hash mismatch — file may have been modified"
        elif stored_hash and current_hash:
            intact = current_hash == stored_hash
            note = "Hash matches stored record" if intact else "Hash mismatch — file may have been modified"
        elif current_hash:
            # First time — store the hash
            _hash_store[asset_id] = current_hash
            intact = True
            note = "Initial hash recorded"
        else:
            intact = True
            note = "No file path provided; integrity check skipped"

        return {
            "intact": intact,
            "hash": current_hash,
            "note": note,
        }

    @staticmethod
    async def generate_custody_report(
        db: Any,
        asset_id: str,
    ) -> dict[str, Any]:
        """Generate a comprehensive custody report for an asset.

        Returns:
            Dict with asset_id, chain, integrity, access_count, unique_users.
        """
        chain = await ChainOfCustodyService.get_custody_chain(db, asset_id)
        integrity = await ChainOfCustodyService.verify_integrity(db, asset_id)

        unique_users = set()
        for entry in chain:
            if entry.get("user"):
                unique_users.add(entry["user"])

        return {
            "asset_id": asset_id,
            "chain": chain,
            "integrity": integrity,
            "access_count": len(chain),
            "unique_users": len(unique_users),
        }

    @staticmethod
    def store_hash(asset_id: str, hash_value: str) -> None:
        """Store a known hash for an asset (for later integrity checks)."""
        _hash_store[asset_id] = hash_value

    @staticmethod
    def clear_store() -> None:
        """Clear in-memory stores (for testing)."""
        _custody_logs.clear()
        _hash_store.clear()
