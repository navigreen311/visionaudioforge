from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDMixin


class Embedding(UUIDMixin, Base):
    __tablename__ = "embeddings"

    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    modality = Column(String(50), nullable=False)
    vector_data = Column(LargeBinary, nullable=True)  # pgvector can be added later
    model_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
