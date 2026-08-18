"""Model export jobs and benchmark results.

An export job produces an artefact and a download URL that a user comes back
for later. Held in a module-level dict, the artefact outlived the record of it:
after a restart the job reported "not found" while the exported file was still
sitting in storage with nothing pointing at it.
"""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelExport(UUIDMixin, TimestampMixin, Base):
    """One export of a model to an edge-optimised format."""

    __tablename__ = "model_exports"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    model_id = Column(String(200), nullable=False)
    format = Column(String(50), nullable=False)
    status = Column(String(32), nullable=False, default="completed")
    optimize = Column(Boolean, nullable=False, default=False)
    quantize = Column(Boolean, nullable=False, default=False)
    file_size_mb = Column(Float, nullable=True)
    download_url = Column(String(1000), nullable=True)
    # Anything format-specific the exporter reported.
    details = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_model_exports_workspace", "workspace_id"),
        Index("ix_model_exports_model", "model_id"),
    )


class EdgeBenchmark(UUIDMixin, TimestampMixin, Base):
    """A benchmark run of an exported model on a device type."""

    __tablename__ = "edge_benchmarks"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    model_id = Column(String(200), nullable=False)
    device_type = Column(String(50), nullable=False, default="")
    results = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_edge_benchmarks_workspace", "workspace_id"),
    )
