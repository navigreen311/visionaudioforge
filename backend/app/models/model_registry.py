import enum

from sqlalchemy import Column, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelStatus(str, enum.Enum):
    registered = "registered"
    staging = "staging"
    production = "production"
    shadow = "shadow"
    archived = "archived"


class ModelRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "model_registry"

    name = Column(String(200), nullable=False)
    version = Column(String(50), nullable=False)
    status = Column(Enum(ModelStatus), nullable=False, default=ModelStatus.registered)
    backbone = Column(String(100), nullable=True)
    metrics = Column(JSON, nullable=False, default=dict)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Relationships
    experiments = relationship("Experiment", back_populates="model")
    workspace = relationship("Workspace", back_populates="models")
