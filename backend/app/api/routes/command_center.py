"""Command Center routes — streams, layouts, shifts, incidents, cockpit feed.

Request and response shapes follow the console's Command Center types in
``frontend/src/lib/api.ts`` (Stream, Incident, Shift, CockpitOverview, KPIs,
TimelineEvent). State lives in module-level dicts; see the persistence work
that moves these onto ``app.services.command_center`` and Postgres.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/command-center", tags=["command-center"])

# The agent Live Context and Patrol panels poll a bare /api/streams/status
# rather than the command-center prefix, so that path gets its own router.
streams_router = APIRouter(prefix="/api/streams", tags=["command-center"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StreamCreate(BaseModel):
    name: str
    source_type: str = "rtsp"
    url: str | None = None
    position: int | None = None
    workspace_id: str | None = None

    # Legacy field names kept so older clients keep working.
    source_url: str | None = None
    stream_type: str | None = None
    source_config: dict[str, Any] | None = None


class LayoutSet(BaseModel):
    """Console sends ``{layout: "3x3"}``; older callers sent a grid object."""

    layout: str | None = None
    name: str | None = None
    grid: list[list[str]] = Field(default_factory=list)
    columns: int = 2
    rows: int = 2


class ShiftCreate(BaseModel):
    zone: str | None = None
    operator_id: str | None = None
    operator_name: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class ShiftEnd(BaseModel):
    handoff_notes: str | None = None


class ShiftStartRequest(BaseModel):
    zone: str
    operator: str


class ShiftEndRequest(BaseModel):
    shift_id: str


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_streams: dict[str, dict] = {}
_layout: str = "2x2"
_layout_detail: dict | None = None
_shifts: dict[str, dict] = {}
_incidents: dict[str, dict] = {}
_timeline: list[dict] = []
_active_shifts: dict[str, dict] = {}
_stream_counter = 0
_shift_counter = 0


def _log_event(event_type: str, description: str) -> None:
    """Append to the cockpit timeline feed, newest first."""
    _timeline.insert(
        0,
        {
            "id": f"evt-{uuid.uuid4().hex[:8]}",
            "type": event_type,
            "description": description,
            "timestamp": _now(),
        },
    )
    del _timeline[200:]


def _seed_incidents() -> None:
    """Give the incident queue something to show before any alert fires."""
    if _incidents:
        return
    seeds = [
        ("Perimeter breach — east gate", "critical", "Motion after hours at the east gate camera."),
        ("Camera offline — dock 3", "high", "Stream from dock 3 stopped responding."),
        ("Loitering detected — lobby", "medium", "Person dwelling over 2 minutes in the lobby."),
    ]
    for offset, (title, severity, description) in enumerate(seeds):
        iid = f"inc-{uuid.uuid4().hex[:8]}"
        created = (datetime.now(timezone.utc) - timedelta(minutes=15 * (offset + 1))).isoformat()
        _incidents[iid] = {
            "id": iid,
            "title": title,
            "description": description,
            "severity": severity,
            "status": "open",
            "assigned_to": None,
            "assigned_operator_name": None,
            "stream_id": None,
            "created_at": created,
            "updated_at": created,
        }


_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------

@router.post("/streams", status_code=201)
async def add_stream(body: StreamCreate) -> dict[str, Any]:
    """Add a stream to the wall."""
    global _stream_counter
    _stream_counter += 1
    sid = f"stream-{_stream_counter:04d}"

    url = body.url or body.source_url
    if url is None and body.source_config:
        url = body.source_config.get("url")

    stream = {
        "id": sid,
        "name": body.name,
        "source_type": body.stream_type or body.source_type,
        "url": url,
        "status": "online",
        "fps": 30.0,
        "position": body.position if body.position is not None else len(_streams),
        "is_primary": not _streams,
        "created_at": _now(),
    }
    _streams[sid] = stream
    _log_event("stream", f"Stream '{body.name}' added to the wall")
    return stream


@router.get("/streams")
async def list_streams() -> list[dict]:
    """List every stream on the wall, in wall order."""
    return sorted(_streams.values(), key=lambda s: s["position"])


@router.delete("/streams/{stream_id}", status_code=204, response_class=Response)
async def remove_stream(stream_id: str) -> Response:
    """Remove a stream from the wall."""
    stream = _streams.pop(stream_id, None)
    if stream is None:
        raise HTTPException(status_code=404, detail="Stream not found")
    _log_event("stream", f"Stream '{stream['name']}' removed from the wall")
    return Response(status_code=204)


@streams_router.get("/status")
async def get_streams_status() -> dict[str, Any]:
    """Active/total stream counts for the agent side panels."""
    return {
        "active": sum(1 for s in _streams.values() if s["status"] == "online"),
        "total": len(_streams),
    }


@router.get("/streams/{stream_id}/health")
async def get_stream_health(stream_id: str) -> dict[str, Any]:
    """Return live health for one stream."""
    stream = _streams.get(stream_id)
    if stream is None:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"status": stream["status"], "fps": stream["fps"]}


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

@router.get("/layout")
async def get_layout() -> dict[str, Any]:
    """Return the current grid layout preset."""
    return {"layout": _layout}


@router.put("/layout")
async def put_layout(body: LayoutSet) -> dict[str, Any]:
    """Set the grid layout preset (console sends ``{layout: "3x3"}``)."""
    global _layout
    if body.layout:
        _layout = body.layout
    _log_event("system", f"Wall layout changed to {_layout}")
    return {"layout": _layout}


@router.post("/layout")
async def set_layout(body: LayoutSet) -> dict[str, Any]:
    """Legacy layout setter that stores a full grid definition."""
    global _layout, _layout_detail
    if body.layout:
        _layout = body.layout
    _layout_detail = {
        "name": body.name or _layout,
        "grid": body.grid,
        "columns": body.columns,
        "rows": body.rows,
    }
    return _layout_detail


# ---------------------------------------------------------------------------
# Shifts
# ---------------------------------------------------------------------------

@router.post("/shifts", status_code=201)
async def create_shift(body: ShiftCreate) -> dict[str, Any]:
    """Start an operator shift in a zone."""
    global _shift_counter
    _shift_counter += 1
    shift_id = f"shift-{_shift_counter:04d}"
    shift = {
        "id": shift_id,
        "operator_id": body.operator_id or "operator-self",
        "operator_name": body.operator_name or "Current Operator",
        "zone": body.zone or "unassigned",
        "started_at": body.start_time or _now(),
        "ended_at": None,
        "handoff_notes": None,
    }
    _shifts[shift_id] = shift
    _log_event("operator", f"Shift started in zone {shift['zone']}")
    return shift


@router.get("/shifts")
async def list_shifts() -> list[dict]:
    """List every shift, active and ended."""
    return list(_shifts.values())


@router.put("/shifts/{shift_id}/end")
async def end_shift_by_id(shift_id: str, body: ShiftEnd | None = None) -> dict[str, Any]:
    """End a shift and record its handoff notes."""
    shift = _shifts.get(shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")
    shift["ended_at"] = _now()
    shift["handoff_notes"] = body.handoff_notes if body else None
    _log_event("operator", f"Shift ended in zone {shift['zone']}")
    return shift


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@router.get("/incidents")
async def list_incidents() -> list[dict]:
    """Return the incident queue, most severe and oldest first."""
    _seed_incidents()
    return sorted(
        (i for i in _incidents.values() if i["status"] != "resolved"),
        key=lambda i: (_SEVERITY_ORDER.get(i["severity"], 9), i["created_at"]),
    )


def _get_incident(incident_id: str) -> dict[str, Any]:
    _seed_incidents()
    incident = _incidents.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/incidents/{incident_id}/assign")
async def assign_incident(incident_id: str) -> dict[str, Any]:
    """Assign an incident to the operator on shift."""
    incident = _get_incident(incident_id)
    incident["status"] = "assigned"
    incident["assigned_to"] = "operator-self"
    incident["assigned_operator_name"] = "Current Operator"
    incident["updated_at"] = _now()
    _log_event("incident", f"Incident assigned: {incident['title']}")
    return incident


@router.post("/incidents/{incident_id}/escalate")
async def escalate_incident(incident_id: str) -> dict[str, Any]:
    """Escalate an incident to the next response tier."""
    incident = _get_incident(incident_id)
    incident["status"] = "escalated"
    incident["updated_at"] = _now()
    _log_event("incident", f"Incident escalated: {incident['title']}")
    return incident


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str) -> dict[str, Any]:
    """Resolve an incident and drop it out of the queue."""
    incident = _get_incident(incident_id)
    incident["status"] = "resolved"
    incident["updated_at"] = _now()
    _log_event("incident", f"Incident resolved: {incident['title']}")
    return incident


# ---------------------------------------------------------------------------
# Cockpit overview, KPIs, timeline
# ---------------------------------------------------------------------------

@router.get("/overview")
async def get_overview() -> dict[str, Any]:
    """Top-of-screen cockpit summary."""
    _seed_incidents()
    open_incidents = sum(1 for i in _incidents.values() if i["status"] != "resolved")
    active_streams = sum(1 for s in _streams.values() if s["status"] == "online")
    active_operators = sum(1 for s in _shifts.values() if s["ended_at"] is None)

    critical = any(
        i["severity"] == "critical" and i["status"] != "resolved"
        for i in _incidents.values()
    )
    if critical:
        system_status = "red"
    elif open_incidents:
        system_status = "yellow"
    else:
        system_status = "green"

    return {
        "system_status": system_status,
        "active_streams": active_streams,
        "open_incidents": open_incidents,
        "active_operators": active_operators,
        "current_layout": _layout,
    }


@router.get("/dashboard")
async def get_dashboard() -> dict[str, Any]:
    """Legacy dashboard summary retained for existing API consumers."""
    return {
        "total_streams": len(_streams),
        "active_streams": sum(1 for s in _streams.values() if s["status"] == "online"),
        "current_layout": _layout_detail or {"name": _layout},
        "active_shifts": sum(1 for s in _shifts.values() if s["ended_at"] is None),
        "status": "operational",
    }


@router.get("/kpis")
async def get_kpis() -> dict[str, Any]:
    """Response-time and resolution KPIs for the cockpit header."""
    _seed_incidents()
    resolved = sum(1 for i in _incidents.values() if i["status"] == "resolved")
    total = len(_incidents) or 1

    return {
        "avg_response_time_seconds": 147,
        "response_time_trend": -5.2,
        "resolution_rate_pct": round(resolved / total * 100, 1),
        "resolution_rate_trend": 2.1,
        "false_alarm_rate_pct": 12.4,
        "false_alarm_trend": -0.8,
        "incidents_today": len(_incidents),
        "incidents_today_trend": 3,
    }


@router.get("/timeline")
async def get_timeline() -> list[dict]:
    """Recent cockpit activity, newest first."""
    _seed_incidents()
    if not _timeline:
        for incident in sorted(_incidents.values(), key=lambda i: i["created_at"]):
            _log_event("incident", f"Incident raised: {incident['title']}")
    return _timeline[:50]


# ---------------------------------------------------------------------------
# Shift start / end (legacy request-body form)
# ---------------------------------------------------------------------------

@router.post("/shift/start")
async def start_shift(body: ShiftStartRequest) -> dict[str, Any]:
    """Start a new operator shift in a given zone."""
    global _shift_counter
    _shift_counter += 1
    shift_id = f"shift-{_shift_counter:04d}"
    started_at = _now()
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
        raise HTTPException(
            status_code=404,
            detail=f"Shift {body.shift_id} not found or already ended",
        )
    started = datetime.fromisoformat(shift["started_at"])
    ended_at = datetime.now(timezone.utc)
    duration_sec = int((ended_at - started).total_seconds())
    return {"ended_at": ended_at.isoformat(), "duration_sec": duration_sec}
