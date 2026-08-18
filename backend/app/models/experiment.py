import enum

from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ExperimentStatus(str, enum.Enum):
    """Lifecycle states for a training experiment.

    Mirrors the `experimentstatus` Postgres enum. Declared as String here, so
    a plain-string assignment was rejected by asyncpg as a datatype mismatch.
    """

    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Experiment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "experiments"

    name = Column(String(255), nullable=False)
    status = Column(
        Enum(ExperimentStatus, name="experimentstatus"),
        nullable=False,
        default=ExperimentStatus.created,
    )
    config = Column(JSON, nullable=True, default=dict)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=True)
    best_epoch = Column(Integer, nullable=True)
    error_message = Column(String(1000), nullable=True)

    epochs = relationship(
        "ExperimentEpoch",
        back_populates="experiment",
        order_by="ExperimentEpoch.epoch_number",
        lazy="selectin",
    )


class ExperimentEpoch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "experiment_epochs"

    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False)
    epoch_number = Column(Integer, nullable=False)
    train_loss = Column(Float, nullable=True)
    val_loss = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    val_accuracy = Column(Float, nullable=True)
    metrics = Column(JSON, nullable=True, default=dict)

    experiment = relationship("Experiment", back_populates="epochs")
