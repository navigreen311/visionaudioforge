"""SQLAlchemy model for knowledge graph edges."""

from sqlalchemy import Column, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import synonym

from app.models.base import Base, TimestampMixin, UUIDMixin


class GraphEdge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "graph_edges"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    source_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False)
    relation = Column(String(255), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    properties = Column(JSON, nullable=False, default=dict)

    # There used to be a second, unregistered GraphEdge in app/models/
    # knowledge_graph.py naming these `edge_type` and `confidence`. It described
    # columns the database does not have, and importing it alongside this one
    # raised "Table 'graph_edges' is already defined", which made every
    # services/knowledge_graph module unimportable. That module is gone; these
    # synonyms keep the services' vocabulary working against the real columns.
    edge_type = synonym("relation")
    confidence = synonym("weight")
