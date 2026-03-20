import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AlertSeverity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class AlertStatus(str, enum.Enum):
    new = "new"
    acknowledged = "acknowledged"
    resolved = "resolved"
    dismissed = "dismissed"


class AlertRule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "alert_rules"

    name = Column(String(200), nullable=False)
    conditions = Column(JSON, nullable=False)
    actions = Column(JSON, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Relationships
    alerts = relationship("Alert", back_populates="rule")


class Alert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    rule_id = Column(UUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.new)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Relationships
    rule = relationship("AlertRule", back_populates="alerts")
    workspace = relationship("Workspace", back_populates="alerts")
