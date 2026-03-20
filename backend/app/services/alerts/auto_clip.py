"""AutoClipService — capture video clips and snapshots on alert triggers."""

import hashlib
import logging
import os
import struct
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Storage root for auto-clip assets
CLIP_STORAGE_ROOT = os.environ.get("CLIP_STORAGE_ROOT", tempfile.gettempdir())


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _build_synthetic_clip(alert_id: str, duration_s: float) -> bytes:
    """Build a minimal AVI file with black frames and alert info.

    V1 implementation: creates a small synthetic binary blob that represents
    a placeholder clip. In production, this would extract buffered frames
    from the capture session.
    """
    header = b"RIFF"
    info = f"ALERT:{alert_id}|DUR:{duration_s}s|TS:{datetime.now(timezone.utc).isoformat()}".encode()
    # Pad to simulate a minimal video file
    padding = b"\x00" * max(0, 1024 - len(info))
    content = info + padding
    size = struct.pack("<I", len(content) + 4)
    return header + size + b"AVI " + content


def _build_placeholder_png(alert_id: str) -> bytes:
    """Build a minimal valid 1x1 PNG with alert metadata embedded.

    V1 placeholder — in production this would save the actual frame.
    """
    # Minimal 1x1 black PNG
    png_header = (
        b"\x89PNG\r\n\x1a\n"  # PNG signature
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
        b"\x18\xd8N"
    )
    # Embed alert ID in a tEXt chunk
    keyword = b"Alert"
    text_data = keyword + b"\x00" + alert_id.encode()
    text_chunk_len = struct.pack(">I", len(text_data))
    text_chunk_type = b"tEXt"
    crc = struct.pack(">I", 0)  # Simplified CRC
    text_chunk = text_chunk_len + text_chunk_type + text_data + crc
    iend = b"\x00\x00\x00\x00IEND\xaeB`\x82"
    return png_header + text_chunk + iend


class AutoClipService:
    """Captures video clips and snapshots when alerts fire."""

    @staticmethod
    async def capture_clip_on_alert(
        alert_id: str,
        source_session_id: Optional[str] = None,
        before_s: float = 10,
        after_s: float = 5,
    ) -> dict[str, Any]:
        """Capture a clip around the alert trigger moment.

        V1: creates a synthetic placeholder clip since real frame buffer
        requires an active capture session. Stores as a file and returns
        metadata suitable for creating an Asset record.

        Returns:
            dict with clip_id, asset_id, duration_s, path, sha256
        """
        clip_id = str(uuid.uuid4())
        asset_id = str(uuid.uuid4())
        duration_s = before_s + after_s

        filename = f"alert_{alert_id}_clip_{clip_id}.avi"
        path = os.path.join(CLIP_STORAGE_ROOT, "clips", filename)
        _ensure_dir(path)

        clip_bytes = _build_synthetic_clip(alert_id, duration_s)
        with open(path, "wb") as f:
            f.write(clip_bytes)

        sha256 = hashlib.sha256(clip_bytes).hexdigest()

        logger.info(
            "Auto-clip captured for alert %s: clip_id=%s, duration=%.1fs, path=%s",
            alert_id, clip_id, duration_s, path,
        )

        return {
            "clip_id": clip_id,
            "asset_id": asset_id,
            "duration_s": duration_s,
            "path": path,
            "sha256": sha256,
            "size_bytes": len(clip_bytes),
            "source_session_id": source_session_id,
            "alert_id": alert_id,
            "type": "video",
        }

    @staticmethod
    async def create_snapshot_on_alert(
        alert_id: str,
        frame: Optional[bytes] = None,
    ) -> dict[str, Any]:
        """Save a snapshot (frame) when an alert triggers.

        If no frame is provided, creates a placeholder PNG.

        Returns:
            dict with snapshot_id, asset_id, path, sha256
        """
        snapshot_id = str(uuid.uuid4())
        asset_id = str(uuid.uuid4())

        filename = f"alert_{alert_id}_snap_{snapshot_id}.png"
        path = os.path.join(CLIP_STORAGE_ROOT, "snapshots", filename)
        _ensure_dir(path)

        image_bytes = frame if frame else _build_placeholder_png(alert_id)
        with open(path, "wb") as f:
            f.write(image_bytes)

        sha256 = hashlib.sha256(image_bytes).hexdigest()

        logger.info(
            "Snapshot captured for alert %s: snapshot_id=%s, path=%s",
            alert_id, snapshot_id, path,
        )

        return {
            "snapshot_id": snapshot_id,
            "asset_id": asset_id,
            "path": path,
            "sha256": sha256,
            "size_bytes": len(image_bytes),
            "alert_id": alert_id,
            "type": "image",
        }
