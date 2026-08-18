"""Provenance tracking and content metadata embedding (LSB steganography)."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provenance import ProvenanceAction, ProvenanceEvent

VALID_ACTIONS = {a.value for a in ProvenanceAction}


class ProvenanceTracker:
    """Track asset provenance and embed/extract content metadata."""

    # ------------------------------------------------------------------
    # Provenance recording
    # ------------------------------------------------------------------

    @staticmethod
    async def record_provenance(
        db: AsyncSession,
        asset_id: str,
        action: str,
        user_id: str,
        details: dict | None = None,
        workspace_id: str | None = None,
    ) -> dict:
        """Append a provenance event for an asset.

        Writes a row and commits. A failure to record raises rather than being
        swallowed: silently dropping an integrity event leaves a chain that
        looks complete but is not, which is the failure mode this whole table
        exists to prevent.
        """
        if action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action '{action}'. Must be one of {VALID_ACTIONS}")

        event = ProvenanceEvent(
            workspace_id=workspace_id,
            asset_id=asset_id,
            action=ProvenanceAction(action),
            user_id=user_id or None,
            details=details or {},
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        return ProvenanceTracker._serialise(event)

    @staticmethod
    async def get_provenance_chain(
        db: AsyncSession,
        asset_id: str,
        workspace_id: str | None = None,
    ) -> list[dict]:
        """Return the full provenance chain for an asset, chronologically."""
        stmt = select(ProvenanceEvent).where(ProvenanceEvent.asset_id == asset_id)
        if workspace_id is not None:
            stmt = stmt.where(ProvenanceEvent.workspace_id == workspace_id)
        stmt = stmt.order_by(ProvenanceEvent.timestamp, ProvenanceEvent.id)

        rows = (await db.execute(stmt)).scalars().all()
        return [ProvenanceTracker._serialise(r) for r in rows]

    @staticmethod
    def _serialise(event: ProvenanceEvent) -> dict:
        """Render a stored event in the shape callers and the API expect."""
        return {
            "id": str(event.id),
            "asset_id": event.asset_id,
            "action": event.action.value
            if isinstance(event.action, ProvenanceAction)
            else str(event.action),
            "user_id": event.user_id,
            "details": event.details or {},
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

    # ------------------------------------------------------------------
    # LSB Steganography — invisible metadata
    # ------------------------------------------------------------------

    @staticmethod
    def add_content_metadata(image: np.ndarray, metadata: dict) -> np.ndarray:
        """Embed *metadata* as JSON in the least-significant bits of pixel data.

        Format: 32-bit length header + UTF-8 JSON payload, each bit stored in
        the LSB of successive pixel channel values.
        """
        payload = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
        payload_bits = []

        # 32-bit length prefix
        length = len(payload)
        for i in range(31, -1, -1):
            payload_bits.append((length >> i) & 1)

        # Payload bits
        for byte in payload:
            for i in range(7, -1, -1):
                payload_bits.append((byte >> i) & 1)

        result = image.copy().ravel()
        total_bits = len(payload_bits)

        if total_bits > len(result):
            raise ValueError("Image too small to embed metadata")

        for i in range(total_bits):
            result[i] = (result[i] & 0xFE) | payload_bits[i]

        return result.reshape(image.shape)

    @staticmethod
    def extract_content_metadata(image: np.ndarray) -> dict | None:
        """Extract LSB-encoded metadata from an image.

        Returns ``None`` if no valid metadata is found.
        """
        flat = image.ravel()

        if len(flat) < 32:
            return None

        # Read 32-bit length
        length = 0
        for i in range(32):
            length = (length << 1) | (int(flat[i]) & 1)

        if length <= 0 or length > 10_000_000:
            return None

        total_bits = 32 + length * 8
        if total_bits > len(flat):
            return None

        # Read payload bytes
        payload_bytes = bytearray()
        for byte_idx in range(length):
            byte_val = 0
            for bit_idx in range(8):
                pos = 32 + byte_idx * 8 + bit_idx
                byte_val = (byte_val << 1) | (int(flat[pos]) & 1)
            payload_bytes.append(byte_val)

        try:
            return json.loads(payload_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    # ------------------------------------------------------------------
    # Synthetic content labeling
    # ------------------------------------------------------------------

    @staticmethod
    def label_synthetic(
        image: np.ndarray, label: str = "AI-GENERATED"
    ) -> np.ndarray:
        """Add visible text overlay and invisible LSB label for synthetic content."""
        import cv2

        result = image.copy()

        # Visible label — bottom-left corner
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = max(0.4, image.shape[1] / 800)
        thickness = max(1, int(font_scale * 2))
        text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
        x = 10
        y = image.shape[0] - 10

        # Background rectangle for readability
        cv2.rectangle(
            result,
            (x - 2, y - text_size[1] - 4),
            (x + text_size[0] + 4, y + 4),
            (0, 0, 0),
            cv2.FILLED,
        )
        cv2.putText(result, label, (x, y), font, font_scale, (255, 255, 255), thickness)

        # Invisible watermark
        result = ProvenanceTracker.add_content_metadata(
            result, {"synthetic": True, "label": label}
        )

        return result
