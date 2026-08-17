"""Evidence integrity models — bundles, chain of custody, integrity baselines.

These back features whose whole purpose is to be trustworthy after the fact.
An in-memory chain of custody is worse than none: it looks like an audit trail
and reports a complete history right up until the process restarts and the
record silently becomes "no accesses recorded". Custody rows are therefore
append-only and written in the same transaction as the access they describe.
"""

import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CustodyAction(str, enum.Enum):
    viewed = "viewed"
    downloaded = "downloaded"
    exported = "exported"
    modified = "modified"
    shared = "shared"
    deleted = "deleted"


class EvidenceBundle(UUIDMixin, TimestampMixin, Base):
    """A collection of evidence assembled around one alert or case."""

    __tablename__ = "evidence_bundles"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    alert_id = Column(String(64), nullable=False)
    case_id = Column(String(64), nullable=True)
    # Snapshot of the alert as it read when the bundle was sealed. Evidence
    # must reflect what was true at collection time, not what the alert row
    # says today.
    alert_snapshot = Column(JSON, nullable=False, default=dict)
    bundle_metadata = Column("metadata", JSON, nullable=False, default=dict)

    items = relationship(
        "EvidenceBundleItem",
        back_populates="bundle",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_evidence_bundles_workspace", "workspace_id"),
        Index("ix_evidence_bundles_alert", "alert_id"),
    )


class EvidenceBundleItem(UUIDMixin, Base):
    """One asset attached to a bundle (clip, snapshot, event, other)."""

    __tablename__ = "evidence_bundle_items"

    bundle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evidence_bundles.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id = Column(String(64), nullable=False)
    asset_type = Column(String(32), nullable=False, default="clip")
    added_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    bundle = relationship("EvidenceBundle", back_populates="items")

    __table_args__ = (
        Index("ix_evidence_bundle_items_bundle", "bundle_id"),
    )


class CustodyEvent(UUIDMixin, Base):
    """One access to a custody-tracked asset. Append-only."""

    __tablename__ = "custody_events"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    asset_id = Column(String(64), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Kept as text as well so the chain still names the actor if the user row
    # is later removed — an audit trail must not lose its subject.
    actor = Column(String(200), nullable=True)
    action = Column(Enum(CustodyAction), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_custody_events_asset_timestamp", "asset_id", "timestamp"),
    )


class AssetIntegrity(UUIDMixin, Base):
    """The known-good hash an asset is checked against.

    Losing this is losing the ability to prove an asset was not tampered with,
    so it is a row rather than a process-local dict.
    """

    __tablename__ = "asset_integrity"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    asset_id = Column(String(64), nullable=False)
    sha256 = Column(String(64), nullable=False)
    recorded_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("asset_id", name="uq_asset_integrity_asset"),
    )
