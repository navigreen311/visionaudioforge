"""In-memory capture session manager (swap for Redis in production)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


class CaptureSessionManager:
    """Create, track, and close capture sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    def create_session(
        self,
        workspace_id: str,
        source_type: str,
        config: dict | None = None,
    ) -> dict:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        session = {
            "session_id": session_id,
            "workspace_id": workspace_id,
            "source_type": source_type,
            "config": config or {},
            "created_at": now.isoformat(),
            "frames_processed": 0,
            "active": True,
        }
        self._sessions[session_id] = session
        return {
            "session_id": session_id,
            "source_type": source_type,
            "created_at": now.isoformat(),
        }

    def end_session(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        session["active"] = False
        created = datetime.fromisoformat(session["created_at"])
        duration = (datetime.now(timezone.utc) - created).total_seconds()
        return {
            "session_id": session_id,
            "duration_s": round(duration, 2),
            "frames_processed": session["frames_processed"],
        }

    def list_active_sessions(self, workspace_id: str) -> list[dict]:
        return [
            {
                "session_id": s["session_id"],
                "source_type": s["source_type"],
                "created_at": s["created_at"],
            }
            for s in self._sessions.values()
            if s["active"] and s["workspace_id"] == workspace_id
        ]

    def increment_frames(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["frames_processed"] += 1

    def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)


# Singleton instance
capture_session_manager = CaptureSessionManager()
