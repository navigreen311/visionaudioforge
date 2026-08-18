"""Pipeline schedules.

Schedules previously lived in a per-instance dict. Writes went into the
pipeline's definition JSON but reads came from memory, so after a restart
``list_schedules`` returned nothing while the rows were still sitting in the
database — a scheduler that silently stops scheduling and reports no schedules
to explain why. Multiple workers each held their own copy, so the answer also
depended on which one you asked.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class PipelineSchedule(UUIDMixin, TimestampMixin, Base):
    """A cron schedule attached to a pipeline."""

    __tablename__ = "pipeline_schedules"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    pipeline_id = Column(UUID(as_uuid=True), nullable=False)
    cron = Column(String(120), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    # Cached so a listing does not have to re-evaluate every cron expression;
    # recomputed from `cron` whenever the schedule is written.
    next_run = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_pipeline_schedules_workspace", "workspace_id"),
        Index("ix_pipeline_schedules_pipeline", "pipeline_id"),
    )
