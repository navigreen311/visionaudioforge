from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"

    filename = Column(String(500), nullable=False)
    media_type = Column(String(50), nullable=False)  # image, video, audio
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    storage_path = Column(String(1000), nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
