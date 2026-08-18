from sqlalchemy import Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, UUIDMixin


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(200), nullable=False)
    payload = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Nullable on purpose. An audit trail whose rows must all name a tenant
    # cannot record the events that happen *before* a tenant is known — above
    # all a failed login, which is the first thing anyone asks an audit log
    # for. It was NOT NULL, so the request-audit middleware had to skip every
    # unauthenticated request, and callers that could not supply a workspace
    # wrapped the insert in a bare except.
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True)

    __table_args__ = (
        Index("ix_audit_logs_workspace_ts", "workspace_id", "timestamp"),
    )
