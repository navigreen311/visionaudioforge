"""Capture session manager backed by Redis.

Capture sessions are ephemeral — a session that outlives a restart has nothing
to resume — so they do not belong in Postgres. What they *do* need is to be
visible from every worker: with a module-level dict, a session opened on one
process was invisible to the next request if it landed elsewhere, which is
why the app could not run more than one worker.

Redis gives shared, expiring state. When no Redis is reachable the manager
falls back to a process-local dict and says so, so single-process development
still works rather than failing outright.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Sessions expire on their own so an abandoned one does not leak forever.
SESSION_TTL_SECONDS = 12 * 60 * 60

_KEY_PREFIX = "vaf:capture:session:"
_WORKSPACE_PREFIX = "vaf:capture:workspace:"


def _session_key(session_id: str) -> str:
    return f"{_KEY_PREFIX}{session_id}"


def _workspace_key(workspace_id: str) -> str:
    return f"{_WORKSPACE_PREFIX}{workspace_id}"


class CaptureSessionManager:
    """Create, track, and close capture sessions.

    Every method is synchronous, matching the previous interface, so callers
    did not have to change. A synchronous Redis client is used for that
    reason.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._local: dict[str, dict] = {}
        self._redis: Any | None = None

        if redis_url is None:
            try:
                from app.config import settings

                redis_url = settings.REDIS_URL
            except Exception:  # noqa: BLE001
                redis_url = None

        if redis_url:
            try:
                import redis as sync_redis  # type: ignore[import-untyped]

                client = sync_redis.from_url(redis_url, decode_responses=True)
                client.ping()
                self._redis = client
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Redis unavailable at %s — capture sessions will not be "
                    "shared between workers",
                    redis_url,
                )

    # ------------------------------------------------------------------
    # Storage helpers
    # ------------------------------------------------------------------

    def _write(self, session: dict) -> None:
        session_id = session["session_id"]
        if self._redis is None:
            self._local[session_id] = session
            return

        self._redis.setex(
            _session_key(session_id), SESSION_TTL_SECONDS, json.dumps(session)
        )
        workspace_key = _workspace_key(session["workspace_id"])
        self._redis.sadd(workspace_key, session_id)
        self._redis.expire(workspace_key, SESSION_TTL_SECONDS)

    def _read(self, session_id: str) -> dict | None:
        if self._redis is None:
            return self._local.get(session_id)

        raw = self._redis.get(_session_key(session_id))
        return json.loads(raw) if raw else None

    def _workspace_sessions(self, workspace_id: str) -> list[dict]:
        if self._redis is None:
            return [
                s
                for s in self._local.values()
                if s["workspace_id"] == workspace_id
            ]

        session_ids = self._redis.smembers(_workspace_key(workspace_id)) or set()
        sessions = []
        for session_id in session_ids:
            session = self._read(session_id)
            if session is None:
                # Expired out from under the index — tidy up as we go.
                self._redis.srem(_workspace_key(workspace_id), session_id)
                continue
            sessions.append(session)
        return sessions

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

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
        self._write(session)

        return {
            "session_id": session_id,
            "source_type": source_type,
            "created_at": now.isoformat(),
        }

    def end_session(self, session_id: str) -> dict:
        session = self._read(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session["active"] = False
        self._write(session)

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
            for s in self._workspace_sessions(workspace_id)
            if s["active"]
        ]

    def increment_frames(self, session_id: str) -> None:
        session = self._read(session_id)
        if session is None:
            return
        session["frames_processed"] += 1
        self._write(session)

    def get_session(self, session_id: str) -> dict | None:
        return self._read(session_id)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def is_shared(self) -> bool:
        """True when sessions are visible to every worker."""
        return self._redis is not None


# Singleton instance
capture_session_manager = CaptureSessionManager()
