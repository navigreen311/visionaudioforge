import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ExperimentStatus(str, enum.Enum):
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"


class Experiment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "experiments"

    name = Column(String(200), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    status = Column(Enum(ExperimentStatus), nullable=False, default=ExperimentStatus.created)
    best_epoch = Column(JSON, nullable=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Relationships
    model = relationship("ModelRecord", back_populates="experiments")
    epochs = relationship("ExperimentEpoch", back_populates="experiment")


class ExperimentEpoch(UUIDMixin, Base):
    __tablename__ = "experiment_epochs"

    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False)
    epoch = Column(Integer, nullable=False)
    metrics = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    experiment = relationship("Experiment", back_populates="epochs")
