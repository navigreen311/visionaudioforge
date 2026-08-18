import enum

from sqlalchemy import Column, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelStatus(str, enum.Enum):
    """Lifecycle states for a registered model.

    These mirror the `modelstatus` Postgres enum the table was created with.
    The column was declared as String here, so inserting a plain string failed
    with a datatype mismatch — registering a model was impossible.
    """

    registered = "registered"
    staging = "staging"
    production = "production"
    shadow = "shadow"
    archived = "archived"


class ModelRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "model_registry"

    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    status = Column(
        Enum(ModelStatus, name="modelstatus"),
        nullable=False,
        default=ModelStatus.registered,
    )
    backbone = Column(String(255), nullable=True)
    metrics = Column(JSON, nullable=True, default=dict)
    tags = Column(ARRAY(String), nullable=True)
    description = Column(Text, nullable=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="models")
