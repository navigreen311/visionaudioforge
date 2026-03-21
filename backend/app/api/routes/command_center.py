"""Command Center routes — streams, layouts, shifts, dashboard."""

from __future__ import annotations

import time
import uuid
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
    zone: str
    operator: str


class ShiftEndRequest(BaseModel):
    shift_id: str


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_streams: dict[str, dict] = {}
_layout: dict | None = None
_shifts: list[dict] = []
_active_shifts: dict[str, dict] = {}
_stream_counter = 0
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
    """Return stub KPI metrics for the Command Center dashboard."""
    return {
        "avg_response_sec": 147,
        "avg_response_delta_pct": -5.2,
        "resolution_rate_pct": 84.3,
        "resolution_rate_delta_pct": 2.1,
        "false_alarm_rate_pct": 12.4,
        "false_alarm_rate_delta_pct": -0.8,
        "incidents_today": 7,
        "incidents_today_delta": 3,
    }


# ---------------------------------------------------------------------------
# Shift start / end
# ---------------------------------------------------------------------------

@router.post("/shift/start")
async def start_shift(body: ShiftStartRequest) -> dict[str, Any]:
    """Start a new operator shift in a given zone."""
    global _shift_counter
    _shift_counter += 1
    shift_id = f"shift-{_shift_counter:04d}"
    started_at = datetime.now(timezone.utc).isoformat()
    _active_shifts[shift_id] = {
        "shift_id": shift_id,
        "zone": body.zone,
        "operator": body.operator,
        "started_at": started_at,
    }
    return {"shift_id": shift_id, "started_at": started_at}


@router.post("/shift/end")
async def end_shift(body: ShiftEndRequest) -> dict[str, Any]:
    """End an active shift and return duration."""
    shift = _active_shifts.pop(body.shift_id, None)
    if shift is None:
        raise HTTPException(status_code=404, detail=f"Shift {body.shift_id} not found or already ended")
    started = datetime.fromisoformat(shift["started_at"])
    ended_at = datetime.now(timezone.utc)
    duration_sec = int((ended_at - started).total_seconds())
    return {"ended_at": ended_at.isoformat(), "duration_sec": duration_sec}
