"""Asset provenance — the recorded history of what was done to an asset.

Provenance is an integrity claim. A chain held in a module-level dict reports a
complete history right up until the process restarts, at which point it
silently becomes "no events recorded" — indistinguishable from an asset nothing
ever touched. That is worse than making no claim at all, so events are rows and
the chain is append-only.
"""

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, UUIDMixin


class ProvenanceAction(str, enum.Enum):
    created = "created"
    transformed = "transformed"
    exported = "exported"
    shared = "shared"
    ai_generated = "ai_generated"
    annotated = "annotated"


class ProvenanceEvent(UUIDMixin, Base):
    """One recorded action against an asset. Append-only.

    There is deliberately no update or delete path: rewriting provenance would
    defeat its purpose.
    """

    __tablename__ = "provenance_events"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    asset_id = Column(String(64), nullable=False)
    action = Column(Enum(ProvenanceAction), nullable=False)
    # Kept as text rather than a users FK so the chain still names who acted
    # even if the user row is later removed. An audit trail must not lose its
    # subject when an account is deleted.
    user_id = Column(String(200), nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # The chain is always read for one asset in chronological order.
        Index("ix_provenance_events_asset_timestamp", "asset_id", "timestamp"),
        Index("ix_provenance_events_workspace", "workspace_id"),
    )
