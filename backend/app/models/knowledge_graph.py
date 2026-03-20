"""Knowledge Graph models — nodes and edges for scene graphs, events, and entity relationships."""

from sqlalchemy import Column, Float, ForeignKey, Index, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class GraphNode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "graph_nodes"

    node_type = Column(String(50), nullable=False)  # person/object/location/event/vehicle
    label = Column(String(200), nullable=False)
    properties = Column(JSON, default=dict, nullable=False)
    embedding = Column(LargeBinary, nullable=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    outgoing_edges = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.source_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    incoming_edges = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.target_id",
        back_populates="target",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_graph_nodes_workspace_type", "workspace_id", "node_type"),
    )


class GraphEdge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "graph_edges"

    source_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    edge_type = Column(String(100), nullable=False)  # contains/near/interacts_with/causes/follows/same_as/appears_in
    properties = Column(JSON, default=dict, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    source = relationship("GraphNode", foreign_keys=[source_id], back_populates="outgoing_edges")
    target = relationship("GraphNode", foreign_keys=[target_id], back_populates="incoming_edges")
