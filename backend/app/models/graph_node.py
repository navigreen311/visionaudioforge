"""SQLAlchemy model for knowledge graph nodes."""

from sqlalchemy import Column, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class GraphNode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "graph_nodes"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    label = Column(String(255), nullable=False)
    node_type = Column(String(100), nullable=False, default="entity")
    properties = Column(JSON, nullable=False, default=dict)
    # GraphService.create_node has always accepted an embedding, but the column
    # did not exist — it was declared only on the duplicate, unregistered model
    # that has since been removed, so the value was silently going nowhere.
    embedding = Column(LargeBinary, nullable=True)
