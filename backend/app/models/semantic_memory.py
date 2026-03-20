"""Semantic Memory model — workspace-scoped long-term memory with scoring, decay, and privacy."""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class MemoryScope(str, enum.Enum):
    global_ = "global"
    workspace = "workspace"
    user = "user"
    agent = "agent"


class SemanticMemory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "semantic_memories"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    scope = Column(
        Enum(MemoryScope, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=MemoryScope.workspace,
    )
    category = Column(String(100), nullable=False)  # fact/event/preference/rule/entity/relationship
    content = Column(Text, nullable=False)
    embedding = Column(LargeBinary, nullable=True)
    importance_score = Column(Float, nullable=False, default=0.5)
    freshness_score = Column(Float, nullable=False, default=1.0)
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    source = Column(String(200), nullable=True)
    source_type = Column(String(50), nullable=False, default="system")  # user/agent/system/inference
    confidence = Column(Float, nullable=False, default=1.0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_private = Column(Boolean, nullable=False, default=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    tags = Column(ARRAY(String), nullable=False, default=list)
    related_memory_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)

    # Relationships
    workspace = relationship("Workspace", backref="semantic_memories")

    __table_args__ = (
        Index("ix_semantic_memories_workspace_scope", "workspace_id", "scope"),
        Index("ix_semantic_memories_workspace_category", "workspace_id", "category"),
        Index("ix_semantic_memories_importance", "importance_score"),
    )
