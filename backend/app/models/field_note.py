"""Field notes captured from the mobile app.

A note written in the field is the one piece of data on that device that exists
nowhere else — it is typed by an operator standing in front of something. Held
in a module-level dict it was lost on the next deploy, silently.
"""

from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class FieldNote(UUIDMixin, TimestampMixin, Base):
    """One note recorded by a field operator."""

    __tablename__ = "field_notes"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    title = Column(String(300), nullable=False, default="")
    content = Column(Text, nullable=False, default="")
    # {"lat": ..., "lon": ...} as sent by the device; kept as a document so a
    # note without a fix is still storable.
    location = Column(JSON, nullable=True)
    tags = Column(ARRAY(String), nullable=False, default=list)
    attachments = Column(ARRAY(String), nullable=False, default=list)

    __table_args__ = (
        Index("ix_field_notes_workspace", "workspace_id"),
    )
