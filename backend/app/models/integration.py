"""Mobile and integration models — push, sync conflicts, webhooks, event log.

A push registration lost on restart means the operator stops receiving
alerts and nothing reports an error. An unresolved sync conflict lost on
restart silently drops one side of an edit made in the field.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


# ---------------------------------------------------------------------------
# Mobile
# ---------------------------------------------------------------------------


class PushDevice(UUIDMixin, TimestampMixin, Base):
    """A device registered to receive push notifications."""

    __tablename__ = "push_devices"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Kept alongside the FK so a registration is still attributable if the
    # user row goes away.
    user_ref = Column(String(64), nullable=False)
    device_token = Column(String(512), nullable=False)
    platform = Column(String(20), nullable=False)
    active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("user_ref", "device_token", name="uq_push_device_token"),
        Index("ix_push_devices_user", "user_ref"),
    )


class PushPreference(UUIDMixin, TimestampMixin, Base):
    """Per-user notification preferences."""

    __tablename__ = "push_preferences"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user_ref = Column(String(64), nullable=False)
    preferences = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("user_ref", name="uq_push_preferences_user"),
    )


class SyncConflict(UUIDMixin, TimestampMixin, Base):
    """A conflict between an offline edit and the server's version.

    Unresolved conflicts are exactly the state that must not be lost: dropping
    one silently discards work someone did in the field.
    """

    __tablename__ = "sync_conflicts"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    local_version = Column(JSON, nullable=False, default=dict)
    server_version = Column(JSON, nullable=False, default=dict)
    resolution = Column(String(32), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_sync_conflicts_workspace", "workspace_id"),
    )


class FieldLocation(UUIDMixin, Base):
    """One recorded position from a field operator's device."""

    __tablename__ = "field_locations"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user_ref = Column(String(64), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy_m = Column(Float, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_field_locations_user_timestamp", "user_ref", "timestamp"),
    )


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------


class Webhook(UUIDMixin, TimestampMixin, Base):
    """An outbound webhook subscription."""

    __tablename__ = "webhooks"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    name = Column(String(200), nullable=False)
    url = Column(String(1000), nullable=False)
    events = Column(JSON, nullable=False, default=list)
    secret = Column(String(200), nullable=True)
    headers = Column(JSON, nullable=False, default=dict)
    active = Column(Boolean, nullable=False, default=True)
    failure_count = Column(Integer, nullable=False, default=0)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)

    deliveries = relationship(
        "WebhookDelivery",
        back_populates="webhook",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_webhooks_workspace", "workspace_id"),
    )


class WebhookDelivery(UUIDMixin, Base):
    """One attempt to deliver an event to a webhook."""

    __tablename__ = "webhook_deliveries"

    webhook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(100), nullable=False)
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    error = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    webhook = relationship("Webhook", back_populates="deliveries")

    __table_args__ = (
        Index("ix_webhook_deliveries_webhook_timestamp", "webhook_id", "timestamp"),
    )


class EventLogEntry(UUIDMixin, Base):
    """An event published on the bus.

    The bus itself is Redis; this is the durable record so the recent-events
    view is the same on every worker instead of showing only what that
    particular process happened to publish.
    """

    __tablename__ = "event_bus_log"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_event_bus_log_workspace_timestamp", "workspace_id", "timestamp"),
    )
