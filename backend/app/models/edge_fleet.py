"""Edge fleet models — devices, OTA rollouts, remote config, packages, syncs.

These replace module-level dicts. Fleet state has to survive a restart and be
visible to every worker process: a device the fleet forgets on deploy is a
device nobody can push an update to.
"""

import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
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


class DeviceStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    degraded = "degraded"


class OTAStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"


class OTADeviceStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"


class EdgeDevice(UUIDMixin, TimestampMixin, Base):
    """A registered edge device."""

    __tablename__ = "edge_devices"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    device_name = Column(String(200), nullable=False)
    device_type = Column(String(50), nullable=False)
    hardware_info = Column(JSON, nullable=False, default=dict)
    network_info = Column(JSON, nullable=False, default=dict)
    api_key = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(
        Enum(DeviceStatus), nullable=False, default=DeviceStatus.online
    )
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    metrics = relationship(
        "DeviceMetric",
        back_populates="device",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    configs = relationship(
        "DeviceConfig",
        back_populates="device",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_edge_devices_workspace_status", "workspace_id", "status"),
    )


class DeviceMetric(UUIDMixin, Base):
    """One heartbeat's worth of telemetry from a device."""

    __tablename__ = "device_metrics"

    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("edge_devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    payload = Column(JSON, nullable=False, default=dict)

    device = relationship("EdgeDevice", back_populates="metrics")

    __table_args__ = (
        Index("ix_device_metrics_device_timestamp", "device_id", "timestamp"),
    )


class OTAUpdate(UUIDMixin, TimestampMixin, Base):
    """An over-the-air model rollout targeting a set of devices."""

    __tablename__ = "ota_updates"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    model_id = Column(String(200), nullable=False)
    previous_model_id = Column(String(200), nullable=True)
    strategy = Column(String(20), nullable=False, default="rolling")
    status = Column(
        Enum(OTAStatus), nullable=False, default=OTAStatus.pending_approval
    )
    scheduled_at = Column(DateTime(timezone=True), nullable=True)

    device_statuses = relationship(
        "OTADeviceRollout",
        back_populates="update",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_ota_updates_workspace", "workspace_id"),
    )


class OTADeviceRollout(UUIDMixin, Base):
    """Per-device progress within one OTA update."""

    __tablename__ = "ota_device_rollouts"

    update_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ota_updates.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(
        Enum(OTADeviceStatus), nullable=False, default=OTADeviceStatus.pending
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    update = relationship("OTAUpdate", back_populates="device_statuses")

    __table_args__ = (
        Index("ix_ota_device_rollouts_update", "update_id"),
    )


class DeviceConfig(UUIDMixin, Base):
    """One version of a device's remote configuration.

    Rows are append-only: the highest ``config_version`` is current, and the
    rest are the history the console diffs against.
    """

    __tablename__ = "device_configs"

    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("edge_devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    config_version = Column(Integer, nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    device = relationship("EdgeDevice", back_populates="configs")

    __table_args__ = (
        UniqueConstraint("device_id", "config_version", name="uq_device_config_version"),
        Index("ix_device_configs_device", "device_id"),
    )


class OfflinePackage(UUIDMixin, TimestampMixin, Base):
    """A built offline deployment bundle."""

    __tablename__ = "offline_packages"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    model_id = Column(String(200), nullable=False)
    device_type = Column(String(50), nullable=False)
    model_format = Column(String(50), nullable=False)
    size_mb = Column(Float, nullable=False, default=0.0)
    contents = Column(JSON, nullable=False, default=list)
    instructions = Column(Text, nullable=False, default="")
    checksum = Column(String(128), nullable=False)

    __table_args__ = (
        Index("ix_offline_packages_workspace", "workspace_id"),
    )


class SyncPlan(UUIDMixin, TimestampMixin, Base):
    """A bandwidth-aware plan for delivering a model to one device."""

    __tablename__ = "sync_plans"

    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("edge_devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id = Column(String(200), nullable=False)
    model_size_mb = Column(Float, nullable=False, default=0.0)
    effective_size_mb = Column(Float, nullable=False, default=0.0)
    available_bandwidth_mbps = Column(Float, nullable=False, default=0.0)
    estimated_time = Column(String(50), nullable=False, default="")
    strategy = Column(String(20), nullable=False, default="full")
    status = Column(String(20), nullable=False, default="created")
    progress_pct = Column(Float, nullable=False, default=0.0)
    transferred_mb = Column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_sync_plans_device", "device_id"),
    )
