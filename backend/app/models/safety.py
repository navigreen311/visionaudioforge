"""Safety and compliance records — scans, legal holds, consent.

All three are the kind of record you produce *because* someone may ask for it
later. Held in module-level dicts they were gone on the next deploy, and the
answer to "was this asset scanned?" or "is it under legal hold?" silently
became no.

Legal holds in particular: a hold exists to stop an asset being deleted. One
that evaporates on restart does not merely lose data, it removes the block
without anyone releasing it.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class SafetyScan(UUIDMixin, TimestampMixin, Base):
    """One safety/privacy scan and what it found."""

    __tablename__ = "safety_scans"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    # The caller's own reference for the scanned thing, when it gave one.
    asset_id = Column(String(128), nullable=True)
    scan_type = Column(String(32), nullable=False, default="image")

    faces_detected = Column(Integer, nullable=False, default=0)
    risk_score = Column(Float, nullable=False, default=0.0)
    # Findings and recommendations as returned to the caller, kept verbatim so
    # the record matches what was reported at the time.
    result = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_safety_scans_workspace", "workspace_id"),
        Index("ix_safety_scans_asset", "asset_id"),
    )


class LegalHold(UUIDMixin, TimestampMixin, Base):
    """A hold preventing deletion of the listed assets."""

    __tablename__ = "legal_holds"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    asset_ids = Column(JSON, nullable=False, default=list)
    reason = Column(Text, nullable=False, default="")
    # Who placed it, as text: the record must still name them if the account
    # is later removed.
    placed_by = Column(String(128), nullable=True)

    released = Column(Boolean, nullable=False, default=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
    released_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_legal_holds_workspace", "workspace_id"),
        Index("ix_legal_holds_released", "released"),
    )


class VoiceConsent(UUIDMixin, Base):
    """Consent from a voice owner for a specific user to clone their voice."""

    __tablename__ = "voice_consents"

    voice_owner_id = Column(String(128), nullable=False)
    user_id = Column(String(128), nullable=False)
    granted_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("voice_owner_id", "user_id", name="uq_voice_consent_pair"),
        Index("ix_voice_consents_owner", "voice_owner_id"),
    )
