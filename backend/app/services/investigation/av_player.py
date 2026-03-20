"""Synced AV playback service — synchronized video, audio, and transcript viewing."""

import base64
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event

logger = logging.getLogger(__name__)


class AVSyncPlayer:
    """Provides synchronized audio/video playback with transcript alignment."""

    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def create_synced_session(
        self,
        video_asset_id: str,
        audio_asset_id: Optional[str] = None,
        transcript: Optional[list[dict]] = None,
    ) -> dict:
        """Create a synced AV playback session.

        Args:
            video_asset_id: UUID of the video asset.
            audio_asset_id: Optional UUID of a separate audio track.
            transcript: Optional list of transcript segments, each with
                        keys: speaker, text, start_s, end_s.

        Returns:
            Session metadata dict.
        """
        session_id = str(uuid4())
        # V1: stub durations — real implementation would probe media files
        video_duration = 120.0
        audio_duration = 120.0 if audio_asset_id else 0.0

        self._sessions[session_id] = {
            "video_asset_id": video_asset_id,
            "audio_asset_id": audio_asset_id,
            "transcript": transcript or [],
            "video_duration_s": video_duration,
            "audio_duration_s": audio_duration,
            "created_at": datetime.utcnow().isoformat(),
        }

        return {
            "session_id": session_id,
            "video_duration_s": video_duration,
            "audio_duration_s": audio_duration,
            "has_transcript": bool(transcript),
        }

    def get_frame_at_time(self, session_id: str, time_s: float) -> dict:
        """Return a video frame at the specified timestamp.

        V1: Returns a stub note about frame extraction.
        Future versions will perform actual frame extraction via ffmpeg.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        # V1 stub — return a placeholder base64 string
        placeholder = base64.b64encode(
            f"[Frame at {time_s:.2f}s from {session['video_asset_id']}]".encode()
        ).decode()

        return {
            "frame": placeholder,
            "timestamp_s": time_s,
        }

    def get_transcript_at_time(
        self,
        session_id: str,
        time_s: float,
        window_s: float = 5.0,
    ) -> list[dict]:
        """Return transcript segments within a time window around the given timestamp.

        Args:
            session_id: Active session identifier.
            time_s: Center timestamp in seconds.
            window_s: Half-window size in seconds (default 5s).

        Returns:
            List of transcript segments overlapping [time_s - window_s, time_s + window_s].
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        start = time_s - window_s
        end = time_s + window_s

        return [
            seg for seg in session.get("transcript", [])
            if seg.get("end_s", 0) >= start and seg.get("start_s", 0) <= end
        ]

    async def get_events_at_time(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        time_s: float,
        window_s: float = 10.0,
    ) -> list[dict]:
        """Return investigation events near a given timestamp.

        Converts time_s offset to a real datetime window relative to the
        earliest event in the workspace, then queries the event table.
        """
        # Find the earliest event as reference point
        ref_result = await db.execute(
            select(Event)
            .where(Event.workspace_id == workspace_id)
            .order_by(Event.timestamp.asc())
            .limit(1)
        )
        ref_event = ref_result.scalar_one_or_none()
        if ref_event is None:
            return []

        from datetime import timedelta

        ref_time = ref_event.timestamp
        center = ref_time + timedelta(seconds=time_s)
        start = center - timedelta(seconds=window_s)
        end = center + timedelta(seconds=window_s)

        result = await db.execute(
            select(Event)
            .where(
                Event.workspace_id == workspace_id,
                Event.timestamp >= start,
                Event.timestamp <= end,
            )
            .order_by(Event.timestamp.asc())
        )
        events = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "type": e.type,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "payload": e.payload,
            }
            for e in events
        ]
