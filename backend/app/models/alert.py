from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin


class AlertRule(TimestampMixin, Base):
    __tablename__ = "alert_rules"

    name = Column(String(255), nullable=False)
    condition = Column(JSON, nullable=False)
    action = Column(String(50), nullable=False, default="notify")
    enabled = Column(String(10), nullable=False, default="true")
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)


class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    rule_id = Column(UUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=False)
    severity = Column(String(50), nullable=False, default="info")
    message = Column(Text, nullable=False)
    acknowledged = Column(String(10), nullable=False, default="false")
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)
