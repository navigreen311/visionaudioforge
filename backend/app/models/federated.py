"""Federated learning: federations, their participants, and training rounds.

The coordinator held federations in a module-level dict and recorded no round
at all, so `/rounds` had nothing to return and the console's training chart
was filled from a generator instead. A federation is a collaboration between
organisations that runs for days — losing it on restart, or losing the record
of which sites contributed to which round, is losing the experiment itself.

Rounds are the audit trail of a federated run: who contributed, how much data
they claimed, and what came out. They are append-only for that reason.
"""

import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class FederationStatus(str, enum.Enum):
    waiting = "waiting"
    ready = "ready"
    training = "training"
    paused = "paused"
    completed = "completed"
    stopped = "stopped"


class ParticipantStatus(str, enum.Enum):
    connected = "connected"
    disconnected = "disconnected"
    reconnecting = "reconnecting"
    removed = "removed"


class RoundStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class Federation(UUIDMixin, TimestampMixin, Base):
    """One federated training collaboration."""

    __tablename__ = "federations"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    name = Column(String(200), nullable=False, default="")
    model_id = Column(String(200), nullable=False, default="")
    status = Column(
        Enum(FederationStatus), nullable=False, default=FederationStatus.waiting
    )
    aggregation_strategy = Column(String(32), nullable=False, default="fedavg")
    min_participants = Column(Integer, nullable=False, default=2)
    total_rounds = Column(Integer, nullable=False, default=20)
    current_round = Column(Integer, nullable=False, default=0)

    # Differential-privacy accounting. Spending is cumulative across rounds and
    # the budget is what stops a federation training indefinitely, so it has to
    # survive a restart or the guarantee is void.
    privacy_budget = Column(Float, nullable=False, default=10.0)
    privacy_epsilon_spent = Column(Float, nullable=False, default=0.0)

    config = Column(JSON, nullable=False, default=dict)
    # Serialised aggregated weights, written by the last completed round.
    global_model = Column(JSON, nullable=True)

    participants = relationship(
        "FederationParticipant",
        back_populates="federation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    rounds = relationship(
        "FederationRound",
        back_populates="federation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_federations_workspace", "workspace_id"),
    )


class FederationParticipant(UUIDMixin, TimestampMixin, Base):
    """A site taking part in a federation."""

    __tablename__ = "federation_participants"

    federation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The site's own identifier, unique within the federation. Not a user or a
    # workspace: a participant is another organisation's node.
    site = Column(String(200), nullable=False)
    name = Column(String(200), nullable=False, default="")
    data_size = Column(Integer, nullable=False, default=0)
    status = Column(
        Enum(ParticipantStatus), nullable=False, default=ParticipantStatus.connected
    )
    joined_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Rounds contributed to and samples claimed, accumulated as updates land.
    rounds_contributed = Column(Integer, nullable=False, default=0)
    samples_contributed = Column(Integer, nullable=False, default=0)
    info = Column(JSON, nullable=False, default=dict)

    federation = relationship("Federation", back_populates="participants")

    __table_args__ = (
        UniqueConstraint("federation_id", "site", name="uq_federation_participant_site"),
        Index("ix_federation_participants_federation", "federation_id"),
    )


class FederationRound(UUIDMixin, Base):
    """One training round: what was distributed, who returned, what aggregated."""

    __tablename__ = "federation_rounds"

    federation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("federations.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_number = Column(Integer, nullable=False)
    status = Column(
        Enum(RoundStatus), nullable=False, default=RoundStatus.in_progress
    )
    global_model_version = Column(String(64), nullable=False, default="")

    participant_count = Column(Integer, nullable=False, default=0)
    updates_received = Column(Integer, nullable=False, default=0)

    # Per-participant submissions for this round, and the averaged result.
    updates = Column(JSON, nullable=False, default=list)
    aggregated_metrics = Column(JSON, nullable=False, default=dict)
    privacy_epsilon_spent = Column(Float, nullable=False, default=0.0)
    aggregation_time_ms = Column(Float, nullable=True)

    started_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at = Column(DateTime(timezone=True), nullable=True)

    federation = relationship("Federation", back_populates="rounds")

    __table_args__ = (
        UniqueConstraint("federation_id", "round_number", name="uq_federation_round_number"),
        Index("ix_federation_rounds_federation", "federation_id"),
    )
