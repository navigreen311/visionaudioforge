"""Command Center routes — streams, layout, shifts, incidents, and dashboard."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.command_center import (
    DashboardOverview,
    IncidentAssign,
    IncidentEscalate,
    IncidentRead,
    KPIs,
    LayoutRead,
    LayoutUpdate,
    QueueStats,
    ShiftCreate,
    ShiftEndRead,
    ShiftEndRequest,
    ShiftRead,
    StreamCreate,
    StreamHealthRead,
    StreamRead,
    TimelineEvent,
    ZoneStatus,
)
from app.services.command_center.dashboard import CockpitDashboard
from app.services.command_center.incident_queue import IncidentQueueService
from app.services.command_center.operator import OperatorService
from app.services.command_center.stream_manager import StreamManager

router = APIRouter(prefix="/api/command-center", tags=["command-center"])


# ── Stream endpoints ──────────────────────────────────────────────────


@router.get("/streams", response_model=list[StreamRead])
async def list_streams(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """List all streams for the workspace."""
    return await StreamManager.list_streams(db, str(workspace_id))


@router.post("/streams", response_model=StreamRead, status_code=201)
async def add_stream(
    body: StreamCreate,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Add a new stream to the workspace."""
    return await StreamManager.add_stream(
        db,
        workspace_id=str(workspace_id),
        name=body.name,
        source_type=body.source_type,
        source_config=body.source_config,
        position=body.position,
    )


@router.delete("/streams/{stream_id}", status_code=200)
async def remove_stream(
    stream_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Remove a stream from the workspace."""
    removed = await StreamManager.remove_stream(db, str(workspace_id), str(stream_id))
    if not removed:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"deleted": True}


# ── Layout endpoints ──────────────────────────────────────────────────


@router.get("/layout", response_model=LayoutRead)
async def get_layout(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get current layout configuration."""
    return await StreamManager.get_layout(db, str(workspace_id))


@router.put("/layout", response_model=LayoutRead)
async def set_layout(
    body: LayoutUpdate,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Set layout preset (2x2, 3x3, 4x4, 1+3, 1+5)."""
    try:
        return await StreamManager.set_layout(db, str(workspace_id), body.layout)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Health endpoint ───────────────────────────────────────────────────


@router.get("/health", response_model=list[StreamHealthRead])
async def stream_health(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get health metrics for all streams."""
    return await StreamManager.get_stream_health(db, str(workspace_id))


# ── Shift endpoints ──────────────────────────────────────────────────


@router.post("/shifts", status_code=201)
async def create_shift(
    body: ShiftCreate,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new operator shift."""
    return await OperatorService.create_shift(
        db,
        workspace_id=str(workspace_id),
        operator_id=body.operator_id,
        start_time=body.start_time,
        end_time=body.end_time,
        zone_assignment=body.zone_assignment,
    )


@router.post("/shifts/{shift_id}/end", response_model=ShiftEndRead)
async def end_shift(
    shift_id: UUID,
    body: ShiftEndRequest = ShiftEndRequest(),
    db: AsyncSession = Depends(get_async_session),
):
    """End an active shift with optional handoff notes."""
    try:
        return await OperatorService.end_shift(db, str(shift_id), handoff_notes=body.handoff_notes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/shifts", response_model=list[ShiftRead])
async def list_shifts(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_session),
):
    """List shifts for the workspace."""
    return await OperatorService.list_shifts(db, str(workspace_id), date=date)


# ── Incident endpoints ───────────────────────────────────────────────


@router.get("/incidents", response_model=list[IncidentRead])
async def get_incident_queue(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    status: str = Query("active", description="Status filter"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get the incident queue sorted by severity then time."""
    return await IncidentQueueService.get_queue(db, str(workspace_id), status=status)


@router.post("/incidents/{incident_id}/assign")
async def assign_incident(
    incident_id: UUID,
    body: IncidentAssign,
    db: AsyncSession = Depends(get_async_session),
):
    """Assign an incident to an operator."""
    try:
        return await IncidentQueueService.assign_incident(db, str(incident_id), body.operator_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/incidents/{incident_id}/escalate")
async def escalate_incident(
    incident_id: UUID,
    body: IncidentEscalate,
    db: AsyncSession = Depends(get_async_session),
):
    """Escalate an incident to a higher level."""
    try:
        return await IncidentQueueService.escalate_incident(db, str(incident_id), body.level)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Dashboard endpoints ──────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardOverview)
async def cockpit_overview(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get the cockpit dashboard overview."""
    return await CockpitDashboard.get_overview(db, str(workspace_id))


@router.get("/kpis", response_model=KPIs)
async def get_kpis(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    period: str = Query("daily", description="Period: hourly, daily, weekly, monthly"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get KPI metrics for the workspace."""
    return await CockpitDashboard.get_kpis(db, str(workspace_id), period=period)


@router.get("/timeline", response_model=list[TimelineEvent])
async def get_timeline(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
):
    """Get the live timeline feed."""
    return await CockpitDashboard.get_timeline_feed(db, str(workspace_id), limit=limit)


@router.get("/zones", response_model=list[ZoneStatus])
async def get_zone_status(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get zone status breakdown."""
    return await CockpitDashboard.get_zone_status(db, str(workspace_id))
