from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin


class ModelRecord(TimestampMixin, Base):
    __tablename__ = "model_registry"

    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="draft")
    backbone = Column(String(255), nullable=True)
    metrics = Column(JSON, nullable=True, default=dict)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
