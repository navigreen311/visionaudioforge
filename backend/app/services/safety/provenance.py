"""Provenance tracking and content metadata embedding (LSB steganography)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np


# In-memory provenance store (for use without a real DB)
_provenance_store: dict[str, list[dict]] = {}

VALID_ACTIONS = {"created", "transformed", "exported", "shared", "ai_generated", "annotated"}


class ProvenanceTracker:
    """Track asset provenance and embed/extract content metadata."""

    # ------------------------------------------------------------------
    # Provenance recording
    # ------------------------------------------------------------------

    @staticmethod
    def record_provenance(
        db: Any,
        asset_id: str,
        action: str,
        user_id: str,
        details: dict | None = None,
    ) -> dict:
        """Record a provenance event for an asset.

        If *db* is ``None``, uses an in-memory store.  Otherwise attempts to
        create an ``AuditLog`` row (best-effort).

        Returns the provenance record dict.
        """
        if action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action '{action}'. Must be one of {VALID_ACTIONS}")

        record = {
            "id": str(uuid.uuid4()),
            "asset_id": asset_id,
            "action": action,
            "user_id": user_id,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Persist to in-memory store
        _provenance_store.setdefault(asset_id, []).append(record)

        # If a real DB session is provided, also persist there
        if db is not None:
            try:
                from app.models.audit_log import AuditLog

                log = AuditLog(
                    user_id=user_id if user_id else None,
                    action=action,
                    resource=f"asset:{asset_id}",
                    payload=record,
                )
                db.add(log)
                db.commit()
            except Exception:
                pass  # fall back to in-memory only

        return record

    @staticmethod
    def get_provenance_chain(db: Any, asset_id: str) -> list[dict]:
        """Return the full provenance chain for an asset, chronologically."""
        return list(_provenance_store.get(asset_id, []))

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
