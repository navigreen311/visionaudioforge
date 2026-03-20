"""SQLAlchemy model for semantic memory entries."""

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class SemanticMemory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "semantic_memories"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, default="general")
    importance = Column(Float, nullable=False, default=0.5)
    access_count = Column(Integer, nullable=False, default=0)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)
