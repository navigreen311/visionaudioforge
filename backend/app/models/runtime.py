"""Inference cost tracking and quota enforcement.

A cost cap that resets on deploy is not a cap. Quotas lived in a per-instance
dict, so every restart returned every workspace to unlimited, and each worker
counted its own usage — a four-worker deployment enforced roughly four times
the configured limit. The spend ledger had the same problem in reverse: cost
reports read as "nothing spent" after a restart.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class InferenceCostEvent(UUIDMixin, Base):
    """One billable inference. Append-only."""

    __tablename__ = "inference_cost_events"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    model_id = Column(String(200), nullable=False)
    latency_ms = Column(Float, nullable=False, default=0.0)
    tokens_or_pixels = Column(Integer, nullable=False, default=0)
    # The rate at the time of the call. Stored per event rather than derived
    # from the current rate table, so re-pricing a model does not silently
    # rewrite what past usage cost.
    cost = Column(Float, nullable=False, default=0.0)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_inference_cost_events_workspace_timestamp",
            "workspace_id",
            "timestamp",
        ),
    )


class WorkspaceQuota(UUIDMixin, TimestampMixin, Base):
    """A workspace's daily inference allowance and its current consumption."""

    __tablename__ = "workspace_quotas"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, unique=True
    )
    daily_limit = Column(Integer, nullable=False, default=0)
    used = Column(Integer, nullable=False, default=0)
    resets_at = Column(DateTime(timezone=True), nullable=True)


class ModelCostRate(UUIDMixin, TimestampMixin, Base):
    """Price per inference for one model.

    Persisted because ``set_model_cost`` is a runtime call: losing the rate
    table on restart silently reverts every model to the default rate and
    changes what usage is billed at, with nothing to show it happened.
    """

    __tablename__ = "model_cost_rates"

    model_id = Column(String(200), nullable=False, unique=True)
    cost_per_unit = Column(Float, nullable=False, default=0.001)
