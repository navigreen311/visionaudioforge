"""Clip recorder — buffer frames in memory then write to disk."""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone

import cv2
import numpy as np


class ClipRecorder:
    """Record video clips and capture snapshots."""

    def __init__(self, output_dir: str, fmt: str = "mp4") -> None:
        self.output_dir = output_dir
        self.fmt = fmt
        os.makedirs(output_dir, exist_ok=True)
        self._recordings: dict[str, dict] = {}

    async def start_recording(
        self, session_id: str, fps: int = 30
    ) -> dict:
        """Begin a new recording. Returns recording metadata."""
        recording_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self._recordings[recording_id] = {
            "session_id": session_id,
            "fps": fps,
            "started_at": now,
            "frames": [],
            "is_recording": True,
        }
        return {
            "recording_id": recording_id,
            "started_at": now.isoformat(),
        }

    async def add_frame(self, recording_id: str, frame: np.ndarray) -> None:
        """Append a frame to the recording buffer."""
        rec = self._recordings.get(recording_id)
        if rec is None:
            raise ValueError(f"Recording {recording_id} not found")
        if not rec["is_recording"]:
            raise ValueError(f"Recording {recording_id} already stopped")
        rec["frames"].append(frame)

    async def stop_recording(self, recording_id: str) -> dict:
        """Finalize the recording and write frames to disk via cv2.VideoWriter."""
        rec = self._recordings.get(recording_id)
        if rec is None:
            raise ValueError(f"Recording {recording_id} not found")

        rec["is_recording"] = False
        frames: list[np.ndarray] = rec["frames"]

        if not frames:
            return {
                "path": "",
                "duration_s": 0.0,
                "frames": 0,
                "size_bytes": 0,
            }

        h, w = frames[0].shape[:2]
        fps = rec["fps"]
        codec = cv2.VideoWriter_fourcc(*"mp4v")
        filename = f"{recording_id}.{self.fmt}"
        path = os.path.join(self.output_dir, filename)

        writer = cv2.VideoWriter(path, codec, fps, (w, h))
        for f in frames:
            writer.write(f)
        writer.release()

        duration_s = len(frames) / fps if fps else 0.0
        size_bytes = os.path.getsize(path) if os.path.exists(path) else 0

        # Free buffered frames
        rec["frames"] = []

        return {
            "path": path,
            "duration_s": round(duration_s, 2),
            "frames": len(frames),
            "size_bytes": size_bytes,
        }

    async def capture_snapshot(
        self, frame: np.ndarray, session_id: str
    ) -> dict:
        """Save a single frame as a PNG snapshot."""
        ts = datetime.now(timezone.utc)
        filename = f"snapshot_{session_id}_{int(time.time())}.png"
        path = os.path.join(self.output_dir, filename)
        cv2.imwrite(path, frame)
        return {"path": path, "timestamp": ts.isoformat()}

    async def get_recording_status(self, recording_id: str) -> dict:
        """Return current status of a recording."""
        rec = self._recordings.get(recording_id)
        if rec is None:
            raise ValueError(f"Recording {recording_id} not found")

        num_frames = len(rec["frames"])
        fps = rec["fps"]
        duration_s = num_frames / fps if fps else 0.0

        return {
            "is_recording": rec["is_recording"],
            "frames_captured": num_frames,
            "duration_s": round(duration_s, 2),
        }
