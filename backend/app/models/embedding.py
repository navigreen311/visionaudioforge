from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin


class Embedding(TimestampMixin, Base):
    __tablename__ = "embeddings"

    source_type = Column(String(50), nullable=False)  # image, audio, text
    source_id = Column(UUID(as_uuid=True), nullable=False)
    model_name = Column(String(255), nullable=False)
    # vector field placeholder — will use pgvector Column(Vector(dim)) when pgvector extension is configured
    vector_data = Column(JSON, nullable=True)  # temporary JSON storage until pgvector is set up
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
