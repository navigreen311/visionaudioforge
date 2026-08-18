"""Agent conversations.

Conversation history was a module-level dict pre-seeded with three invented
threads, so a fresh install showed transcripts of troubleshooting sessions
nobody had run — and anything a user actually said was lost on restart.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AgentConversation(UUIDMixin, TimestampMixin, Base):
    """One thread of messages between a user and an agent."""

    __tablename__ = "agent_conversations"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    title = Column(String(300), nullable=False, default="")
    # Text rather than an agents FK: agents are addressed by slug in this API
    # and a conversation should outlive the agent definition it used.
    agent_id = Column(String(200), nullable=True)

    messages = relationship(
        "AgentMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AgentMessage.timestamp",
    )

    __table_args__ = (
        Index("ix_agent_conversations_workspace", "workspace_id"),
    )


class AgentMessage(UUIDMixin, Base):
    """One message in a conversation. Append-only."""

    __tablename__ = "agent_messages"

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(32), nullable=False, default="user")
    content = Column(Text, nullable=False, default="")
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation = relationship("AgentConversation", back_populates="messages")

    __table_args__ = (
        Index("ix_agent_messages_conversation_timestamp", "conversation_id", "timestamp"),
    )
