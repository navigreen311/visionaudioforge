"""Pydantic schemas for Command Center endpoints."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Stream schemas ────────────────────────────────────────────────────

class StreamCreate(BaseModel):
    name: str
    source_type: str
    source_config: dict[str, Any] = Field(default_factory=dict)
    position: Optional[int] = None


class StreamRead(BaseModel):
    stream_id: str
    name: str
    source_type: str
    position: int
    status: str

    model_config = {"from_attributes": True}


class StreamHealthRead(BaseModel):
    stream_id: str
    status: str
    fps: float
    latency_ms: float
    last_frame: Optional[str] = None


# ── Layout schemas ────────────────────────────────────────────────────

class LayoutRead(BaseModel):
    layout: str
    streams: list[dict[str, Any]] = Field(default_factory=list)


class LayoutUpdate(BaseModel):
    layout: str = Field(..., pattern=r"^(2x2|3x3|4x4|1\+3|1\+5)$")


# ── Shift schemas ─────────────────────────────────────────────────────

class ShiftCreate(BaseModel):
    operator_id: str
    start_time: datetime
    end_time: datetime
    zone_assignment: Optional[str] = None


class ShiftRead(BaseModel):
    shift_id: str
    operator_id: str
    start_time: str
    end_time: Optional[str] = None
    zone_assignment: Optional[str] = None
    is_active: bool = True
    handoff_notes: Optional[str] = None
    events_handled: int = 0

    model_config = {"from_attributes": True}


class ShiftEndRequest(BaseModel):
    handoff_notes: Optional[str] = None


class ShiftEndRead(BaseModel):
    shift_id: str
    duration_h: float
    events_handled: int


# ── Incident schemas ──────────────────────────────────────────────────

class IncidentAssign(BaseModel):
    operator_id: str


class IncidentEscalate(BaseModel):
    level: int


class IncidentRead(BaseModel):
    incident_id: str
    title: str
    severity: str
    status: str
    assigned_to: Optional[str] = None
    escalation_level: int = 0
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class QueueStats(BaseModel):
    total_active: int
    by_severity: dict[str, int]
    avg_response_time_s: float
    unassigned: int
    oldest_unresolved_age_s: float


# ── Dashboard schemas ─────────────────────────────────────────────────

class DashboardOverview(BaseModel):
    active_streams: int
    active_operators: int
    open_incidents: int
    alerts_24h: int
    streams_health: dict[str, Any]
    system_status: str


class ZoneStatus(BaseModel):
    zone: str
    streams: int
    incidents: int
    operator: Optional[str] = None


class TimelineEvent(BaseModel):
    id: str
    type: str
    summary: str
    timestamp: str
    payload: Optional[dict[str, Any]] = None


class KPIs(BaseModel):
    avg_response_time_s: float
    incident_resolution_rate: float
    false_alarm_rate: float
    uptime_pct: float
