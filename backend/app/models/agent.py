from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Agent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agents"

    name = Column(String(200), nullable=False)
    agent_type = Column(String(100), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="idle")
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Relationships
    memories = relationship("AgentMemory", back_populates="agent")
    workspace = relationship("Workspace", back_populates="agents")


class AgentMemory(UUIDMixin, Base):
    __tablename__ = "agent_memories"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    content = Column(Text, nullable=False)
    importance_score = Column(Float, nullable=False, default=0.5)
    freshness_score = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="memories")
