"""Event fusion engine for cross-modal event correlation and timeline building."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class EventFusionEngine:
    """Fuse events from multiple modalities based on temporal proximity."""

    def fuse_events(
        self, events: list[dict[str, Any]], time_window_s: float = 5.0
    ) -> list[dict[str, Any]]:
        """Group events by temporal proximity and merge across modalities.

        Args:
            events: List of event dicts, each must have ``timestamp`` (ISO str or
                datetime) and ``modality`` (str).
            time_window_s: Maximum gap in seconds for events to be grouped.

        Returns:
            List of FusedEvent dicts.
        """
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: self._parse_ts(e["timestamp"]))

        groups: list[list[dict]] = []
        current_group: list[dict] = [sorted_events[0]]

        for ev in sorted_events[1:]:
            last_ts = self._parse_ts(current_group[-1]["timestamp"])
            cur_ts = self._parse_ts(ev["timestamp"])
            gap = abs((cur_ts - last_ts).total_seconds())
            if gap <= time_window_s:
                current_group.append(ev)
            else:
                groups.append(current_group)
                current_group = [ev]
        groups.append(current_group)

        fused: list[dict] = []
        for group in groups:
            modalities = list({e.get("modality", "unknown") for e in group})
            confidences = [e.get("confidence", 0.5) for e in group]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            # Boost confidence when multiple modalities agree
            if len(modalities) > 1:
                avg_confidence = min(1.0, avg_confidence * 1.2)

            earliest_ts = min(self._parse_ts(e["timestamp"]) for e in group)
            summary_parts = []
            for m in modalities:
                count = sum(1 for e in group if e.get("modality") == m)
                summary_parts.append(f"{count} {m} event(s)")
            summary = "Fused: " + ", ".join(summary_parts)

            fused.append({
                "fused_id": str(uuid.uuid4()),
                "timestamp": earliest_ts.isoformat(),
                "events": group,
                "modalities": modalities,
                "confidence": round(avg_confidence, 4),
                "summary": summary,
            })

        return fused

    def temporal_alignment(
        self,
        vision_events: list[dict[str, Any]],
        audio_events: list[dict[str, Any]],
        tolerance_ms: float = 500,
    ) -> list[tuple[dict, dict]]:
        """Match vision events with audio events within tolerance.

        Args:
            vision_events: Events from vision modality (each has ``timestamp``).
            audio_events: Events from audio modality (each has ``timestamp``).
            tolerance_ms: Maximum time difference in milliseconds.

        Returns:
            List of (vision_event, audio_event) aligned pairs.
        """
        tolerance_s = tolerance_ms / 1000.0
        pairs: list[tuple[dict, dict]] = []
        used_audio: set[int] = set()

        for v_ev in vision_events:
            v_ts = self._parse_ts(v_ev["timestamp"])
            best_idx: int | None = None
            best_gap = float("inf")
            for i, a_ev in enumerate(audio_events):
                if i in used_audio:
                    continue
                a_ts = self._parse_ts(a_ev["timestamp"])
                gap = abs((v_ts - a_ts).total_seconds())
                if gap <= tolerance_s and gap < best_gap:
                    best_gap = gap
                    best_idx = i
            if best_idx is not None:
                used_audio.add(best_idx)
                pairs.append((v_ev, audio_events[best_idx]))

        return pairs

    async def build_multimodal_timeline(
        self,
        db: Any,
        workspace_id: str,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Query all events in a time range, fuse, and return a timeline.

        Args:
            db: Async database session.
            workspace_id: Workspace UUID string.
            start: ISO timestamp for range start.
            end: ISO timestamp for range end.

        Returns:
            Chronological list of timeline entries.
        """
        start_dt = self._parse_ts(start)
        end_dt = self._parse_ts(end)

        events: list[dict] = []
        try:
            from sqlalchemy import select
            from app.models.event import Event

            stmt = (
                select(Event)
                .where(Event.workspace_id == uuid.UUID(workspace_id))
                .where(Event.timestamp >= start_dt)
                .where(Event.timestamp <= end_dt)
                .order_by(Event.timestamp)
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()
            for row in rows:
                payload = row.payload or {}
                events.append({
                    "id": str(row.id),
                    "timestamp": row.timestamp.isoformat(),
                    "type": row.type,
                    "modality": payload.get("modality", row.type.split("_")[0] if "_" in row.type else "unknown"),
                    "confidence": payload.get("confidence", 0.5),
                    "payload": payload,
                })
        except Exception:
            logger.warning("Database query failed for timeline — returning empty list")
            return []

        if not events:
            return []

        fused = self.fuse_events(events)
        timeline = []
        for f in fused:
            timeline.append({
                "timestamp": f["timestamp"],
                "events": f["events"],
                "modalities": f["modalities"],
                "type": "fused" if len(f["modalities"]) > 1 else f["modalities"][0],
            })

        return sorted(timeline, key=lambda t: t["timestamp"])

    def cross_modal_alert(
        self,
        vision_event: dict[str, Any],
        audio_event: dict[str, Any],
        rule: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Generate an alert when vision and audio agree per a rule.

        Args:
            vision_event: Vision detection event (e.g., motion detected).
            audio_event: Audio detection event (e.g., loud sound).
            rule: Dict with ``vision_type`` and ``audio_type`` to match, plus
                optional ``min_confidence``.

        Returns:
            Alert dict or ``None`` if the rule doesn't match.
        """
        v_type = vision_event.get("type", "")
        a_type = audio_event.get("type", "")

        if v_type != rule.get("vision_type") or a_type != rule.get("audio_type"):
            return None

        min_conf = rule.get("min_confidence", 0.0)
        v_conf = vision_event.get("confidence", 0.5)
        a_conf = audio_event.get("confidence", 0.5)

        combined_confidence = min(1.0, (v_conf + a_conf) / 2 * 1.3)
        if combined_confidence < min_conf:
            return None

        return {
            "alert_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vision_event": vision_event,
            "audio_event": audio_event,
            "rule": rule,
            "confidence": round(combined_confidence, 4),
            "message": f"Cross-modal alert: {v_type} + {a_type} detected",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_ts(ts: str | datetime) -> datetime:
        """Parse an ISO timestamp string or pass through a datetime."""
        if isinstance(ts, datetime):
            return ts
        # Handle Z suffix
        ts_str = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_str)
