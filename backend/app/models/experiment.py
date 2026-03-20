from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin


class Experiment(TimestampMixin, Base):
    __tablename__ = "experiments"

    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    config = Column(JSON, nullable=True, default=dict)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=True)


class ExperimentEpoch(TimestampMixin, Base):
    __tablename__ = "experiment_epochs"

    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False)
    epoch_number = Column(Integer, nullable=False)
    train_loss = Column(Float, nullable=True)
    val_loss = Column(Float, nullable=True)
    metrics = Column(JSON, nullable=True, default=dict)
