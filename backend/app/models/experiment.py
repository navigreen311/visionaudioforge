from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Experiment(TimestampMixin, Base):
    __tablename__ = "experiments"

    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="created")
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


class ExperimentEpoch(TimestampMixin, Base):
    __tablename__ = "experiment_epochs"

    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False)
    epoch_number = Column(Integer, nullable=False)
    train_loss = Column(Float, nullable=True)
    val_loss = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    val_accuracy = Column(Float, nullable=True)
    metrics = Column(JSON, nullable=True, default=dict)

    experiment = relationship("Experiment", back_populates="epochs")
