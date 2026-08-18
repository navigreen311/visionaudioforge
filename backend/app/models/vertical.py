"""Installed vertical packs.

Installation state lived in two module-level dicts — one in the routes, one in
services/verticals/installer.py — which disagreed with each other and both
emptied on restart. A workspace that had installed the Security pack reported
nothing installed after a deploy, while the pack's pipelines and alert presets
were still expected to be in place.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class InstalledVerticalPack(UUIDMixin, TimestampMixin, Base):
    """One vertical pack installed into one workspace."""

    __tablename__ = "installed_vertical_packs"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    pack_id = Column(String(64), nullable=False)
    installed_version = Column(String(32), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    # Per-component toggles, keyed by component slug. Stored as documents
    # because the component list is defined by the pack, not by this schema.
    enabled_modules = Column(JSON, nullable=False, default=dict)
    enabled_pipelines = Column(JSON, nullable=False, default=dict)
    enabled_alerts = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        # A pack is installed at most once per workspace; re-installing updates.
        UniqueConstraint("workspace_id", "pack_id", name="uq_installed_pack_workspace"),
        Index("ix_installed_vertical_packs_workspace", "workspace_id"),
    )


class VerticalInstallJob(UUIDMixin, TimestampMixin, Base):
    """A record of one install attempt and its per-step progress."""

    __tablename__ = "vertical_install_jobs"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    pack_id = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    steps = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        Index("ix_vertical_install_jobs_workspace", "workspace_id"),
    )
