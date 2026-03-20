from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    name = Column(String(255), nullable=False)
    agent_type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=True, default=dict)
    status = Column(String(50), nullable=False, default="idle")
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)


class AgentMemory(TimestampMixin, Base):
    __tablename__ = "agent_memories"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)
