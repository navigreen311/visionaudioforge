"""Notifications, one row per recipient.

The notification bell was served from a module-level list of five hardcoded
entries — "Critical alert triggered / Person detected in Zone B", dated
2026-04-13 — returned to every user of every workspace. Marking one read mutated
that shared list, so one person's click cleared the badge for every tenant on
the deployment, and a restart brought all five back unread.

Read state is per recipient, which is why a notification is one row per user
rather than one row per event with a join table: a bell that says "3 unread"
means three things *you* have not seen. Producers fan out to the workspace's
users when the event happens (`NotificationService.emit`), so the read state is
a plain column and the common query — this user's unread count — is a single
indexed count with no join.

The cost is N rows per event, which is the right trade at the size of team this
console is for. If a workspace ever grows past a few hundred users, the fan-out
moves to a background task; nothing about the read model has to change.
"""

from __future__ import annotations

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class NotificationType(str, enum.Enum):
    """What kind of event produced this notification.

    These four are the categories the console's `NotificationItem` renders an
    icon for. A producer that does not fit one of them belongs in `system`
    rather than in a new value the console will draw as a blank.
    """

    alert = "alert"
    pipeline = "pipeline"
    model = "model"
    system = "system"


class Notification(UUIDMixin, TimestampMixin, Base):
    """One notification, addressed to one user."""

    __tablename__ = "notifications"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    # The recipient. Carrying it explicitly rather than deriving it from the
    # workspace is what makes read state per-person.
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    # Where the bell takes you. Nullable: not every event has a page.
    action_url = Column(String(500), nullable=True)

    # Null means unread. A timestamp rather than a boolean because "when did
    # they see it" is the question anyone asks next, and it costs nothing now.
    read_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # The bell's two queries: this user's list, newest first, and their
        # unread count. Both are served by this one index.
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_unread", "user_id", "read_at"),
        Index("ix_notifications_workspace", "workspace_id"),
    )
