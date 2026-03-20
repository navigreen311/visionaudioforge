from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin


class Dataset(TimestampMixin, Base):
    __tablename__ = "datasets"

    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    format = Column(String(50), nullable=False, default="unknown")
    size_bytes = Column(Integer, nullable=True)
    item_count = Column(Integer, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
