from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "model_registry"

    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="registered")
    backbone = Column(String(255), nullable=True)
    metrics = Column(JSON, nullable=True, default=dict)
    tags = Column(ARRAY(String), nullable=True)
    description = Column(Text, nullable=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="models")
