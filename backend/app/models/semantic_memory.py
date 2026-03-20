"""SQLAlchemy model for semantic memory entries."""

import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class MemoryScope(str, enum.Enum):
    workspace = "workspace"
    user = "user"
    global_ = "global"


class SemanticMemory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "semantic_memories"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, default="general")
    scope = Column(String(50), nullable=False, default="workspace")
    importance = Column(Float, nullable=False, default=0.5)
    importance_score = Column(Float, nullable=False, default=0.5)
    freshness_score = Column(Float, nullable=False, default=1.0)
    access_count = Column(Integer, nullable=False, default=0)
    source = Column(String(255), nullable=True)
    source_type = Column(String(50), nullable=False, default="system")
    confidence = Column(Float, nullable=False, default=1.0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    is_private = Column(Boolean, nullable=False, default=False)
    owner_id = Column(UUID(as_uuid=True), nullable=True)
    tags = Column(ARRAY(String), nullable=False, default=list)
    related_memory_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)
