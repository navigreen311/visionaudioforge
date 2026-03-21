"""Command Center routes — streams, layouts, shifts, dashboard, KPIs."""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/command-center", tags=["command-center"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StreamCreate(BaseModel):
    name: str
    source_url: str
    stream_type: str = "rtsp"
    workspace_id: str | None = None


class LayoutSet(BaseModel):
    name: str
    grid: list[list[str]] = Field(default_factory=list)
    columns: int = 2
    rows: int = 2


class ShiftCreate(BaseModel):
    operator_id: str
    start_time: str
    end_time: str
    zone: str | None = None


class ShiftStartRequest(BaseModel):
    zone: str = "Zone A"


class ShiftEndRequest(BaseModel):
    handoff_notes: str | None = None


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_streams: dict[str, dict] = {}
_layout: dict | None = None
_shifts: list[dict] = []
_stream_counter = 0
_active_shift: dict | None = None
_shift_counter = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/streams")
async def add_stream(body: StreamCreate) -> dict[str, Any]:
    global _stream_counter
    _stream_counter += 1
    sid = f"stream-{_stream_counter:04d}"
    stream = {"id": sid, "name": body.name, "source_url": body.source_url, "type": body.stream_type, "status": "active"}
    _streams[sid] = stream
    return stream


@router.get("/streams")
async def list_streams() -> list[dict]:
    return list(_streams.values())


@router.post("/layout")
async def set_layout(body: LayoutSet) -> dict[str, Any]:
    global _layout
    _layout = {"name": body.name, "grid": body.grid, "columns": body.columns, "rows": body.rows}
    return _layout


@router.get("/layout")
async def get_layout() -> dict[str, Any]:
    return _layout or {"name": "default", "grid": [], "columns": 2, "rows": 2}


@router.post("/shifts")
async def create_shift(body: ShiftCreate) -> dict[str, Any]:
    shift = {
        "id": f"shift-{len(_shifts) + 1:04d}",
        "operator_id": body.operator_id,
        "start_time": body.start_time,
        "end_time": body.end_time,
        "zone": body.zone,
        "created_at": time.time(),
    }
    _shifts.append(shift)
    return shift


@router.get("/shifts")
async def list_shifts() -> list[dict]:
    return _shifts


@router.get("/dashboard")
async def get_dashboard() -> dict[str, Any]:
    return {
        "total_streams": len(_streams),
        "active_streams": sum(1 for s in _streams.values() if s["status"] == "active"),
        "current_layout": _layout or {"name": "default"},
        "active_shifts": len(_shifts),
        "status": "operational",
    }


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

@router.get("/kpis")
async def get_kpis() -> dict[str, Any]:
    """Return current KPI snapshot (stub with realistic random data)."""
    return {
        "avg_response_time_seconds": round(random.uniform(8, 45), 1),
        "response_time_trend": round(random.uniform(-5, 5), 1),
        "resolution_rate_pct": round(random.uniform(85, 99), 1),
        "resolution_rate_trend": round(random.uniform(-3, 3), 1),
        "false_alarm_rate_pct": round(random.uniform(2, 15), 1),
        "false_alarm_trend": round(random.uniform(-4, 4), 1),
        "incidents_today": random.randint(0, 25),
        "incidents_today_trend": round(random.uniform(-10, 10), 1),
    }


# ---------------------------------------------------------------------------
# Shift start / end (CC6)
# ---------------------------------------------------------------------------

@router.post("/shift/start")
async def start_shift(body: ShiftStartRequest) -> dict[str, Any]:
    """Start an operator shift. Returns the active shift object."""
    global _active_shift, _shift_counter
    if _active_shift and not _active_shift.get("ended_at"):
        raise HTTPException(status_code=409, detail="A shift is already active")
    _shift_counter += 1
    now = datetime.now(timezone.utc).isoformat()
    _active_shift = {
        "id": f"shift-{_shift_counter:04d}",
        "operator_id": "op-default",
        "operator_name": "Operator",
        "zone": body.zone,
        "started_at": now,
        "ended_at": None,
        "handoff_notes": None,
    }
    return _active_shift


@router.post("/shift/end")
async def end_shift(body: ShiftEndRequest | None = None) -> dict[str, Any]:
    """End the active shift."""
    global _active_shift
    if not _active_shift or _active_shift.get("ended_at"):
        raise HTTPException(status_code=404, detail="No active shift to end")
    _active_shift["ended_at"] = datetime.now(timezone.utc).isoformat()
    if body and body.handoff_notes:
        _active_shift["handoff_notes"] = body.handoff_notes
    result = dict(_active_shift)
    _active_shift = None
    return result
