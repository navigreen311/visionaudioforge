from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin


class Pipeline(TimestampMixin, Base):
    __tablename__ = "pipelines"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False, default=dict)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)


class PipelineRun(TimestampMixin, Base):
    __tablename__ = "pipeline_runs"

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
