"""Command Center routes — streams, layouts, shifts, incidents, cockpit feed.

State lives in Postgres via ``app.services.command_center``; these handlers
translate between those services and the console's Command Center types in
``frontend/src/lib/api.ts`` (Stream, Incident, Shift, CockpitOverview, KPIs,
TimelineEvent).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.command_center import (
    CommandStream,
    Incident,
    IncidentStatus,
    OperatorShift,
    StreamStatus,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.services.command_center.dashboard import CockpitDashboard
from app.services.command_center.incident_queue import IncidentQueueService
from app.services.command_center.operator import OperatorService
from app.services.command_center.stream_manager import StreamManager

router = APIRouter(prefix="/api/command-center", tags=["command-center"])

# The agent Live Context and Patrol panels poll a bare /api/streams/status
# rather than the command-center prefix, so that path gets its own router.
streams_router = APIRouter(prefix="/api/streams", tags=["command-center"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StreamCreate(BaseModel):
    name: str
    source_type: str = "rtsp"
    url: str | None = None
    position: int | None = None

    # Legacy field names kept so older clients keep working.
    source_url: str | None = None
    stream_type: str | None = None
    source_config: dict[str, Any] | None = None

    def resolved_source_type(self) -> str:
        return self.stream_type or self.source_type

    def resolved_config(self) -> dict[str, Any]:
        config = dict(self.source_config or {})
        url = self.url or self.source_url or config.get("url")
        if url:
            config["url"] = url
        return config


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
    start_time: str | None = None
    end_time: str | None = None


class ShiftEnd(BaseModel):
    handoff_notes: str | None = None


class ShiftStartRequest(BaseModel):
    zone: str
    operator: str | None = None


class ShiftEndRequest(BaseModel):
    shift_id: str


# ---------------------------------------------------------------------------
# Translation between storage and console vocabularies
# ---------------------------------------------------------------------------

# The database tracks transport-level stream state; the console shows an
# operator-level traffic light.
_STATUS_TO_CONSOLE = {
    StreamStatus.connected: "online",
    StreamStatus.disconnected: "offline",
    StreamStatus.error: "offline",
    StreamStatus.buffering: "degraded",
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _stream_out(stream: CommandStream) -> dict[str, Any]:
    config = stream.source_config or {}
    return {
        "id": str(stream.id),
        "name": stream.name,
        "source_type": stream.source_type.value,
        "url": config.get("url"),
        "status": _STATUS_TO_CONSOLE.get(stream.status, "offline"),
        "fps": stream.fps or 0.0,
        "position": stream.position,
        "is_primary": bool(stream.is_priority),
        "created_at": _iso(stream.created_at),
    }


def _shift_out(shift: OperatorShift, operator_name: str | None = None) -> dict[str, Any]:
    # end_time is set at creation as the shift's *planned* end. The console
    # reads ended_at as "this shift is over", so only report it once the shift
    # is no longer active.
    return {
        "id": str(shift.id),
        "operator_id": str(shift.operator_id),
        "operator_name": operator_name or "",
        "zone": shift.zone_assignment or "",
        "started_at": _iso(shift.start_time),
        "ended_at": _iso(shift.end_time) if not shift.is_active else None,
        "handoff_notes": shift.handoff_notes,
    }


def _incident_out(
    incident: Incident, operator_name: str | None = None
) -> dict[str, Any]:
    return {
        "id": str(incident.id),
        "title": incident.title,
        "description": incident.description or "",
        "severity": incident.severity.value,
        "status": incident.status.value,
        "assigned_to": str(incident.assigned_to) if incident.assigned_to else None,
        "assigned_operator_name": operator_name,
        "stream_id": (
            str(incident.source_stream_id) if incident.source_stream_id else None
        ),
        "created_at": _iso(incident.created_at),
        "updated_at": _iso(incident.updated_at),
    }


async def _load_stream(
    db: AsyncSession, stream_id: str
) -> CommandStream:
    try:
        key = uuid.UUID(stream_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail="Stream not found")

    result = await db.execute(select(CommandStream).where(CommandStream.id == key))
    stream = result.scalar_one_or_none()
    if stream is None:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream


async def _load_incident(db: AsyncSession, incident_id: str) -> Incident:
    try:
        key = uuid.UUID(incident_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail="Incident not found")

    result = await db.execute(select(Incident).where(Incident.id == key))
    incident = result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


async def _operator_name(db: AsyncSession, operator_id) -> str | None:
    if operator_id is None:
        return None
    result = await db.execute(select(User.email).where(User.id == operator_id))
    return result.scalar_one_or_none()


async def _resolve_operator(
    db: AsyncSession, workspace_id: uuid.UUID, operator_id: str | None
) -> uuid.UUID:
    """Pick the operator a shift belongs to.

    The console's Start Shift control sends only a zone — it has no operator to
    send until the authenticated-user dependency lands. Until then an explicit
    operator_id wins, and otherwise the shift is attributed to the workspace
    owner.
    """
    if operator_id:
        try:
            return uuid.UUID(operator_id)
        except (ValueError, AttributeError, TypeError):
            raise HTTPException(status_code=422, detail="operator_id is not a valid UUID")

    result = await db.execute(
        select(Workspace.owner_id).where(Workspace.id == workspace_id)
    )
    owner_id = result.scalar_one_or_none()
    if owner_id is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "No operator for this shift: pass operator_id, or set an owner "
                "on the workspace."
            ),
        )
    return owner_id


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------

@router.post("/streams", status_code=201)
async def add_stream(
    body: StreamCreate,
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add a stream to the wall."""
    try:
        created = await StreamManager.add_stream(
            db,
            str(workspace_id),
            name=body.name,
            source_type=body.resolved_source_type(),
            source_config=body.resolved_config(),
            position=body.position,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return _stream_out(await _load_stream(db, created["stream_id"]))


@router.get("/streams")
async def list_streams(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List every stream on the wall, in wall order."""
    result = await db.execute(
        select(CommandStream)
        .where(CommandStream.workspace_id == workspace_id)
        .order_by(CommandStream.position)
    )
    return [_stream_out(s) for s in result.scalars().all()]


@router.delete("/streams/{stream_id}", status_code=204, response_class=Response)
async def remove_stream(
    stream_id: str,
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a stream from the wall."""
    removed = await StreamManager.remove_stream(db, str(workspace_id), stream_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Stream not found")
    return Response(status_code=204)


@router.get("/streams/{stream_id}/health")
async def get_stream_health(
    stream_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return live health for one stream."""
    stream = await _load_stream(db, stream_id)
    return {
        "status": _STATUS_TO_CONSOLE.get(stream.status, "offline"),
        "fps": stream.fps or 0.0,
        "latency_ms": stream.latency_ms,
    }


@streams_router.get("/status")
async def get_streams_status(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Active/total stream counts for the agent side panels."""
    result = await db.execute(
        select(CommandStream.status).where(
            CommandStream.workspace_id == workspace_id
        )
    )
    statuses = list(result.scalars().all())
    return {
        "active": sum(1 for s in statuses if s == StreamStatus.connected),
        "total": len(statuses),
    }


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

@router.get("/layout")
async def get_layout(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the current grid layout preset."""
    layout = await StreamManager.get_layout(db, str(workspace_id))
    return {"layout": layout["layout"]}


@router.put("/layout")
async def put_layout(
    body: LayoutSet,
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Set the grid layout preset (console sends ``{layout: "3x3"}``)."""
    if not body.layout:
        raise HTTPException(status_code=422, detail="layout is required")

    try:
        result = await StreamManager.set_layout(db, str(workspace_id), body.layout)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"layout": result["layout"]}


@router.post("/layout")
async def set_layout(
    body: LayoutSet,
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Legacy layout setter."""
    layout = body.layout or body.name or "2x2"
    try:
        result = await StreamManager.set_layout(db, str(workspace_id), layout)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "name": layout,
        "layout": result["layout"],
        "grid": body.grid,
        "columns": body.columns,
        "rows": body.rows,
    }


# ---------------------------------------------------------------------------
# Shifts
# ---------------------------------------------------------------------------

@router.post("/shifts", status_code=201)
async def create_shift(
    body: ShiftCreate,
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start an operator shift in a zone."""
    operator_id = await _resolve_operator(db, workspace_id, body.operator_id)

    start = (
        datetime.fromisoformat(body.start_time)
        if body.start_time
        else datetime.now(timezone.utc)
    )
    end = (
        datetime.fromisoformat(body.end_time)
        if body.end_time
        else start + timedelta(hours=8)
    )

    created = await OperatorService.create_shift(
        db,
        str(workspace_id),
        str(operator_id),
        start,
        end,
        zone_assignment=body.zone,
    )

    result = await db.execute(
        select(OperatorShift).where(OperatorShift.id == uuid.UUID(created["shift_id"]))
    )
    shift = result.scalar_one()
    return _shift_out(shift, await _operator_name(db, shift.operator_id))


@router.get("/shifts")
async def list_shifts(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List every shift, active and ended."""
    result = await db.execute(
        select(OperatorShift)
        .where(OperatorShift.workspace_id == workspace_id)
        .order_by(OperatorShift.start_time.desc())
    )
    shifts = list(result.scalars().all())
    return [
        _shift_out(s, await _operator_name(db, s.operator_id)) for s in shifts
    ]


@router.put("/shifts/{shift_id}/end")
async def end_shift_by_id(
    shift_id: str,
    body: ShiftEnd | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """End a shift and record its handoff notes."""
    try:
        await OperatorService.end_shift(
            db, shift_id, handoff_notes=body.handoff_notes if body else None
        )
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Shift not found")

    result = await db.execute(
        select(OperatorShift).where(OperatorShift.id == uuid.UUID(shift_id))
    )
    shift = result.scalar_one()
    return _shift_out(shift, await _operator_name(db, shift.operator_id))


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@router.get("/incidents")
async def list_incidents(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    status: str = Query("active", description="active | resolved | dismissed"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the incident queue, most severe and oldest first."""
    queue = await IncidentQueueService.get_queue(db, str(workspace_id), status=status)

    incidents = []
    for entry in queue:
        incident = await _load_incident(db, entry["incident_id"])
        incidents.append(
            _incident_out(incident, await _operator_name(db, incident.assigned_to))
        )
    return incidents


@router.post("/incidents/{incident_id}/assign")
async def assign_incident(
    incident_id: str,
    operator_id: str | None = Query(None, description="Operator to assign to"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Assign an incident to an operator."""
    incident = await _load_incident(db, incident_id)
    assignee = await _resolve_operator(db, incident.workspace_id, operator_id)

    await IncidentQueueService.assign_incident(db, incident_id, str(assignee))

    await db.refresh(incident)
    return _incident_out(incident, await _operator_name(db, incident.assigned_to))


@router.post("/incidents/{incident_id}/escalate")
async def escalate_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Escalate an incident to the next response tier."""
    incident = await _load_incident(db, incident_id)
    await IncidentQueueService.escalate_incident(
        db, incident_id, incident.escalation_level + 1
    )

    await db.refresh(incident)
    return _incident_out(incident, await _operator_name(db, incident.assigned_to))


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Resolve an incident and drop it out of the queue."""
    incident = await _load_incident(db, incident_id)

    incident.status = IncidentStatus.resolved
    incident.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(incident)

    return _incident_out(incident, await _operator_name(db, incident.assigned_to))


# ---------------------------------------------------------------------------
# Cockpit overview, KPIs, timeline
# ---------------------------------------------------------------------------

# The dashboard service speaks healthy/warning/critical; the console renders a
# green/yellow/red light.
_SYSTEM_STATUS_TO_CONSOLE = {
    "healthy": "green",
    "warning": "yellow",
    "critical": "red",
}


@router.get("/overview")
async def get_overview(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Top-of-screen cockpit summary."""
    overview = await CockpitDashboard.get_overview(db, str(workspace_id))
    layout = await StreamManager.get_layout(db, str(workspace_id))

    return {
        "system_status": _SYSTEM_STATUS_TO_CONSOLE.get(
            overview["system_status"], "yellow"
        ),
        "active_streams": overview["active_streams"],
        "open_incidents": overview["open_incidents"],
        "active_operators": overview["active_operators"],
        "current_layout": layout["layout"],
    }


@router.get("/dashboard")
async def get_dashboard(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Full cockpit overview, including per-status stream health."""
    overview = await CockpitDashboard.get_overview(db, str(workspace_id))
    layout = await StreamManager.get_layout(db, str(workspace_id))
    return {**overview, "current_layout": layout["layout"]}


@router.get("/kpis")
async def get_kpis(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    period: str = Query("daily", description="hourly | daily | weekly | monthly"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Response-time and resolution KPIs for the cockpit header."""
    kpis = await CockpitDashboard.get_kpis(db, str(workspace_id), period=period)

    incidents_today = await CockpitDashboard.get_overview(db, str(workspace_id))

    return {
        "avg_response_time_seconds": round(kpis.get("avg_response_time_s", 0.0), 1),
        "response_time_trend": 0.0,
        "resolution_rate_pct": round(kpis.get("incident_resolution_rate", 0.0) * 100, 1),
        "resolution_rate_trend": 0.0,
        "false_alarm_rate_pct": round(kpis.get("false_alarm_rate", 0.0) * 100, 1),
        "false_alarm_trend": 0.0,
        "incidents_today": incidents_today["open_incidents"],
        "incidents_today_trend": 0,
    }


@router.get("/timeline")
async def get_timeline(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Recent cockpit activity, newest first."""
    feed = await CockpitDashboard.get_timeline_feed(
        db, str(workspace_id), limit=limit
    )
    return [
        {
            "id": entry["id"],
            "type": _timeline_type(entry["type"]),
            "description": entry["summary"],
            "timestamp": entry["timestamp"],
        }
        for entry in feed
    ]


def _timeline_type(raw: str) -> str:
    """Map an event type onto the console's TimelineEvent union."""
    if raw == "incident":
        return "incident"
    if raw.startswith("alert"):
        return "alert"
    if raw.startswith("stream"):
        return "stream"
    if raw.startswith("operator") or raw.startswith("shift"):
        return "operator"
    return "system"


# ---------------------------------------------------------------------------
# Shift start / end (legacy request-body form)
# ---------------------------------------------------------------------------

@router.post("/shift/start")
async def start_shift(
    body: ShiftStartRequest,
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start a new operator shift in a given zone."""
    operator_id = await _resolve_operator(db, workspace_id, body.operator)
    start = datetime.now(timezone.utc)

    created = await OperatorService.create_shift(
        db,
        str(workspace_id),
        str(operator_id),
        start,
        start + timedelta(hours=8),
        zone_assignment=body.zone,
    )
    return {"shift_id": created["shift_id"], "started_at": start.isoformat()}


@router.post("/shift/end")
async def end_shift(
    body: ShiftEndRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """End an active shift and return duration."""
    try:
        result = await OperatorService.end_shift(db, body.shift_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=404,
            detail=f"Shift {body.shift_id} not found or already ended",
        )

    return {
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "duration_sec": int(result["duration_h"] * 3600),
    }
