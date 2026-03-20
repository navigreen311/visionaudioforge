import enum

from sqlalchemy import Column, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class PlanType(str, enum.Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class Workspace(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"

    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    plan = Column(Enum(PlanType), nullable=False, default=PlanType.free)
    settings = Column(JSON, nullable=False, default=dict)

    # Relationships
    users = relationship("User", back_populates="workspace", foreign_keys="User.workspace_id")
    models = relationship("ModelRecord", back_populates="workspace")
    datasets = relationship("Dataset", back_populates="workspace")
    pipelines = relationship("Pipeline", back_populates="workspace")
    alerts = relationship("Alert", back_populates="workspace")
    agents = relationship("Agent", back_populates="workspace")
