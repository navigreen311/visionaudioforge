"""SQLAlchemy models for the Command Center — streams, shifts, and incidents."""

import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class StreamSourceType(str, enum.Enum):
    rtsp = "rtsp"
    hls = "hls"
    webrtc = "webrtc"
    file = "file"
    usb = "usb"
    # The console's stream picker offers these two alongside rtsp.
    camera = "camera"
    screen = "screen"


class StreamStatus(str, enum.Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"
    buffering = "buffering"


class IncidentSeverity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class IncidentStatus(str, enum.Enum):
    active = "active"
    assigned = "assigned"
    escalated = "escalated"
    resolved = "resolved"
    dismissed = "dismissed"


class CommandStream(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "command_streams"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(200), nullable=False)
    source_type = Column(Enum(StreamSourceType), nullable=False)
    source_config = Column(JSON, nullable=False, default=dict)
    position = Column(Integer, nullable=False, default=0)
    status = Column(Enum(StreamStatus), nullable=False, default=StreamStatus.connected)
    fps = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)
    last_frame_at = Column(DateTime(timezone=True), nullable=True)
    pinned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_priority = Column(Integer, nullable=False, default=0)


class CommandLayout(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "command_layouts"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, unique=True)
    layout = Column(String(10), nullable=False, default="2x2")


class OperatorShift(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "operator_shifts"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    zone_assignment = Column(String(200), nullable=True)
    handoff_notes = Column(Text, nullable=True)
    events_handled = Column(Integer, nullable=False, default=0)
    is_active = Column(Integer, nullable=False, default=1)


class Incident(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "incidents"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(Enum(IncidentSeverity), nullable=False, default=IncidentSeverity.medium)
    status = Column(Enum(IncidentStatus), nullable=False, default=IncidentStatus.active)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    escalation_level = Column(Integer, nullable=False, default=0)
    source_stream_id = Column(UUID(as_uuid=True), ForeignKey("command_streams.id"), nullable=True)
    payload = Column(JSON, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    response_time_s = Column(Float, nullable=True)


class OperatorActionLog(UUIDMixin, Base):
    __tablename__ = "operator_action_logs"

    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String(200), nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
