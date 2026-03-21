"""Dashboard API routes — aggregate stats and recent activity."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    active_streams: int = 0
    streams_history: list[int] = []
    models_production: int = 0
    models_history: list[int] = []
    open_alerts: int = 0
    alerts_history: list[int] = []
    total_assets: int = 0
    assets_history: list[int] = []


class ActivityItem(BaseModel):
    type: str
    message: str
    timestamp: str
    severity: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RANGE_LENGTHS: dict[str, int] = {
    "7d": 7,
    "14d": 14,
    "30d": 30,
}


def _zero_history(range_key: str) -> list[int]:
    """Return a zero-filled list matching the requested range."""
    length = _RANGE_LENGTHS.get(range_key, 7)
    return [0] * length


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(range: str = Query("7d", alias="range")):
    """Aggregate dashboard statistics.

    Returns stub zeroes — will be wired to real services later.
    """
    history = _zero_history(range)
    return DashboardStats(
        active_streams=0,
        streams_history=history,
        models_production=0,
        models_history=history,
        open_alerts=0,
        alerts_history=history,
        total_assets=0,
        assets_history=history,
    )


@router.get("/activity", response_model=list[ActivityItem])
async def dashboard_activity(limit: int = Query(20, ge=1, le=100)):
    """Recent activity feed.

    Returns an empty list — will be wired to real event sources later.
    """
    return []
