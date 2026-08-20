import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class PipelineRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class Pipeline(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pipelines"

    name = Column(String(200), nullable=False)
    # PipelineCreate accepts a description and PipelineRead promises one on
    # every read, but the column did not exist — so both write routes raised
    # TypeError and answered 500, and no pipeline could be saved by any client.
    # Nullable: the console's save sends only name and definition.
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="1.0")
    definition = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="draft")
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Relationships
    runs = relationship("PipelineRun", back_populates="pipeline")
    workspace = relationship("Workspace", back_populates="pipelines")


class PipelineRun(UUIDMixin, Base):
    __tablename__ = "pipeline_runs"

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=False)
    status = Column(Enum(PipelineRunStatus), nullable=False, default=PipelineRunStatus.pending)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    results = Column(JSON, nullable=True)

    # Relationships
    pipeline = relationship("Pipeline", back_populates="runs")
