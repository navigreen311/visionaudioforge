"""Plugin and marketplace models — registrations, installs, custom nodes, BYOM.

A plugin registration that vanishes on restart takes its pipelines with it:
a pipeline referencing a custom node stops resolving, and an installed
marketplace plugin silently un-installs itself.
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
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Plugin(UUIDMixin, TimestampMixin, Base):
    """A plugin registered against a workspace from its manifest."""

    __tablename__ = "plugins"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    name = Column(String(200), nullable=False)
    version = Column(String(50), nullable=False, default="1.0.0")
    author = Column(String(200), nullable=False, default="")
    description = Column(Text, nullable=False, default="")
    category = Column(String(50), nullable=False)
    entry_point = Column(String(500), nullable=False, default="")
    permissions = Column(JSON, nullable=False, default=list)
    config_schema = Column(JSON, nullable=False, default=dict)
    config = Column(JSON, nullable=False, default=dict)
    icon_url = Column(String(500), nullable=True)
    enabled = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default="registered")
    install_count = Column(Integer, nullable=False, default=0)

    reviews = relationship(
        "PluginReview",
        back_populates="plugin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_plugins_workspace", "workspace_id"),
    )


class PluginReview(UUIDMixin, Base):
    """A rating and comment left on a plugin."""

    __tablename__ = "plugin_reviews"

    plugin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plugins.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating = Column(Float, nullable=False)
    comment = Column(Text, nullable=True)
    author = Column(String(200), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plugin = relationship("Plugin", back_populates="reviews")

    __table_args__ = (
        Index("ix_plugin_reviews_plugin", "plugin_id"),
    )


class InstalledPlugin(UUIDMixin, TimestampMixin, Base):
    """A marketplace plugin installed into a workspace."""

    __tablename__ = "installed_plugins"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    name = Column(String(200), nullable=False)
    version = Column(String(50), nullable=False)
    latest_version = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False, default="")
    description = Column(Text, nullable=False, default="")
    author = Column(String(200), nullable=False, default="")
    status = Column(String(50), nullable=False, default="active")
    used_in_pipelines = Column(Integer, nullable=False, default=0)
    config = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_installed_plugins_workspace", "workspace_id"),
    )


class CustomNode(UUIDMixin, TimestampMixin, Base):
    """A pipeline node authored through the node SDK.

    Scaffolded code has to outlive the request that generated it — a pipeline
    referencing a node whose definition is gone cannot run.
    """

    __tablename__ = "custom_nodes"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False, default="Custom")
    description = Column(Text, nullable=False, default="")
    code = Column(Text, nullable=False, default="")
    input_schema = Column(JSON, nullable=False, default=dict)
    output_schema = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="draft")
    node_metadata = Column("metadata", JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_custom_nodes_workspace", "workspace_id"),
    )


class ModelAdapter(UUIDMixin, TimestampMixin, Base):
    """A registered inference adapter for a user-supplied model.

    The loaded model object itself stays in a process-local cache — it is a
    live handle, not data — but the registration that says where to load it
    from has to survive a restart.
    """

    __tablename__ = "model_adapters"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    model_id = Column(UUID(as_uuid=True), nullable=False)
    model_name = Column(String(200), nullable=False)
    model_path_or_url = Column(String(1000), nullable=False)
    framework = Column(String(50), nullable=False)
    input_schema = Column(JSON, nullable=False, default=dict)
    output_schema = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="registered")

    __table_args__ = (
        Index("ix_model_adapters_workspace", "workspace_id"),
    )


class BYOMModel(UUIDMixin, TimestampMixin, Base):
    """A user-supplied model registered through Bring Your Own Model."""

    __tablename__ = "byom_models"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    model_name = Column(String(200), nullable=False)
    model_type = Column(String(50), nullable=False)
    file_name = Column(String(500), nullable=False, default="")
    input_shape = Column(String(100), nullable=False, default="")
    output_shape = Column(String(100), nullable=False, default="")
    adapter = Column(JSON, nullable=False, default=dict)
    node_name = Column(String(200), nullable=True)
    node_config = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="ready")

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "model_name", name="uq_byom_workspace_model_name"
        ),
        Index("ix_byom_models_workspace", "workspace_id"),
    )
