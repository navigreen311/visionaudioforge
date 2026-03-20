import enum

from sqlalchemy import BigInteger, Column, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class AssetType(str, enum.Enum):
    image = "image"
    video = "video"
    audio = "audio"


class Asset(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assets"

    type = Column(Enum(AssetType), nullable=False)
    path = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    size_bytes = Column(BigInteger, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)
    tags = Column(ARRAY(String), nullable=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    __table_args__ = (
        Index("ix_assets_workspace_type", "workspace_id", "type"),
        Index("ix_assets_tags", "tags"),
    )
