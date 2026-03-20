import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModalityType(str, enum.Enum):
    image = "image"
    video = "video"
    audio = "audio"
    multimodal = "multimodal"


class Dataset(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "datasets"

    name = Column(String(200), nullable=False)
    modality = Column(Enum(ModalityType), nullable=False)
    version = Column(String(50), nullable=False, default="1.0")
    stats = Column(JSON, nullable=False, default=dict)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    sample_count = Column(Integer, nullable=False, default=0)

    # Relationships
    workspace = relationship("Workspace", back_populates="datasets")
