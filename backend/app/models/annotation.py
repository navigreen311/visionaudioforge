"""Annotation model for storing asset annotations."""

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class Annotation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "annotations"

    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    annotation_type = Column(String(50), nullable=False)
    data = Column(JSON, nullable=False, default=dict)
    is_verified = Column(Boolean, default=False, nullable=False)
