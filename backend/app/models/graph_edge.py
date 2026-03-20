"""SQLAlchemy model for knowledge graph edges."""

from sqlalchemy import Column, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class GraphEdge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "graph_edges"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    source_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False)
    relation = Column(String(255), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    properties = Column(JSON, nullable=False, default=dict)
