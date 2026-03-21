"""Memory dashboard routes — summary, timeline, decay-all (ME4 + ME5 stubs)."""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/memory", tags=["memory-dashboard"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ImportanceBucket(BaseModel):
    bucket: str
    count: int
    level: str  # "low" | "medium" | "high" | "critical"


class FreshnessBucket(BaseModel):
    label: str
    count: int
    color: str  # "green" | "yellow" | "orange" | "red"


class SummaryResponse(BaseModel):
    total: int
    avg_importance: float
    high_importance_count: int
    private_count: int
    by_category: dict[str, int]
    importance_distribution: list[ImportanceBucket]
    freshness_distribution: list[FreshnessBucket]


class TimelineEvent(BaseModel):
    id: str
    event_type: str  # "created" | "accessed" | "decayed" | "edited"
    content: str
    category: str
    importance: float = Field(ge=0.0, le=1.0)
    timestamp: str  # ISO-8601


class DecayAllResponse(BaseModel):
    decayed_count: int
    new_avg_freshness: float


# ---------------------------------------------------------------------------
# Mock data generators
# ---------------------------------------------------------------------------

def _mock_summary() -> dict[str, Any]:
    return {
        "total": 142,
        "avg_importance": 0.634,
        "high_importance_count": 38,
        "private_count": 12,
        "by_category": {
            "fact": 45,
            "event": 28,
            "preference": 22,
            "rule": 18,
            "entity": 16,
            "relationship": 13,
        },
        "importance_distribution": [
            {"bucket": "0.0-0.2", "count": 12, "level": "low"},
            {"bucket": "0.2-0.4", "count": 24, "level": "low"},
            {"bucket": "0.4-0.6", "count": 42, "level": "medium"},
            {"bucket": "0.6-0.8", "count": 38, "level": "high"},
            {"bucket": "0.8-1.0", "count": 26, "level": "critical"},
        ],
        "freshness_distribution": [
            {"label": "Fresh (< 1d)", "count": 34, "color": "green"},
            {"label": "Recent (1-7d)", "count": 52, "color": "yellow"},
            {"label": "Aging (7-30d)", "count": 38, "color": "orange"},
            {"label": "Stale (> 30d)", "count": 18, "color": "red"},
        ],
    }


def _mock_timeline() -> list[dict[str, Any]]:
    now = _dt.datetime.now(_dt.timezone.utc)
    events: list[dict[str, Any]] = []
    samples = [
        ("created", "User prefers dark mode for all dashboards", "preference", 0.72),
        ("accessed", "Project deadline is March 30 2026", "event", 0.85),
        ("edited", "API rate limit changed from 100 to 200 req/min", "rule", 0.91),
        ("decayed", "Old meeting notes from January standup", "event", 0.23),
        ("created", "Main database is PostgreSQL 16 on RDS", "fact", 0.88),
        ("accessed", "Team member Alex handles frontend reviews", "relationship", 0.65),
        ("created", "Preferred notification channel is Slack #alerts", "preference", 0.54),
        ("decayed", "Temporary debug flag was enabled for pipeline", "fact", 0.18),
        ("edited", "Auth provider switched from Auth0 to Clerk", "fact", 0.93),
        ("accessed", "Workspace has 8 active agents deployed", "entity", 0.77),
        ("created", "Backup schedule runs daily at 02:00 UTC", "rule", 0.69),
        ("decayed", "Test fixture data from last sprint", "fact", 0.15),
        ("created", "User timezone is America/New_York", "preference", 0.41),
        ("accessed", "Vision pipeline version 2.4.1 is deployed", "entity", 0.62),
        ("edited", "Memory retention policy updated to 90 days", "rule", 0.80),
    ]

    for i, (etype, content, category, importance) in enumerate(samples):
        # Spread events across last 5 days
        offset = _dt.timedelta(hours=i * 8, minutes=i * 13)
        ts = now - offset
        events.append({
            "id": str(uuid.uuid4()),
            "event_type": etype,
            "content": content,
            "category": category,
            "importance": importance,
            "timestamp": ts.isoformat(),
        })

    return events


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=SummaryResponse)
async def get_memory_summary() -> dict[str, Any]:
    """Return aggregate statistics for the memory dashboard (ME4)."""
    return _mock_summary()


@router.get("/timeline", response_model=list[TimelineEvent])
async def get_memory_timeline(
    start: str | None = Query(None, description="ISO date filter start"),
    end: str | None = Query(None, description="ISO date filter end"),
) -> list[dict[str, Any]]:
    """Return a chronological list of memory events (ME5)."""
    events = _mock_timeline()

    # Apply optional date filters
    if start:
        try:
            start_dt = _dt.datetime.fromisoformat(start)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=_dt.timezone.utc)
            events = [e for e in events if _dt.datetime.fromisoformat(e["timestamp"]) >= start_dt]
        except ValueError:
            pass  # ignore malformed date

    if end:
        try:
            end_dt = _dt.datetime.fromisoformat(end)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=_dt.timezone.utc)
            events = [e for e in events if _dt.datetime.fromisoformat(e["timestamp"]) <= end_dt]
        except ValueError:
            pass

    return events


@router.post("/decay-all", response_model=DecayAllResponse)
async def decay_all_memories() -> dict[str, Any]:
    """Apply global decay to all memory freshness scores (stub)."""
    return {"decayed_count": 142, "new_avg_freshness": 0.521}
