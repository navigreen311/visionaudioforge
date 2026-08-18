"""Persisted settings — appearance preferences and workspace integrations.

Both were module-level stores. Appearance preferences were additionally keyed
by the literal string "default", so every user shared one row's worth of state:
changing your theme changed everybody's, until a restart reset it for everybody
at once.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class AppearancePreference(UUIDMixin, TimestampMixin, Base):
    """One user's console appearance settings.

    ``user_id`` is nullable so the endpoint keeps working for unauthenticated
    callers, which is how the console reaches it today; that row is the shared
    fallback. Once a caller is authenticated they get their own row.
    """

    __tablename__ = "appearance_preferences"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    # Stored as a document rather than a column per setting: this is a UI
    # preference blob that the console owns, and adding a control should not
    # require a migration.
    preferences = Column(JSON, nullable=False, default=dict)


class WorkspaceIntegration(UUIDMixin, TimestampMixin, Base):
    """A third-party integration configured for a workspace."""

    __tablename__ = "workspace_integrations"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    name = Column(String(200), nullable=False)
    type = Column(String(64), nullable=False, default="")
    enabled = Column(Boolean, nullable=False, default=False)
    config = Column(JSON, nullable=False, default=dict)
    connected_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_workspace_integrations_workspace", "workspace_id"),
    )
