from sqlalchemy import Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID

from app.models.base import Base, UUIDMixin


class Event(UUIDMixin, Base):
    __tablename__ = "events"

    type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source = Column(String(100), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    linked_asset_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)

    __table_args__ = (
        Index("ix_events_workspace_type_ts", "workspace_id", "type", "timestamp"),
    )
