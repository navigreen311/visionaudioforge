"""Edge fleet persistence

Moves the edge fleet off module-level dicts: device registry, telemetry,
OTA rollouts, remote config versions, offline packages and sync plans.

Revision ID: 002
Revises: 001
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


# create_type=False: the types are created once, explicitly, in upgrade().
# Left at the default, create_table() would try to create each one again.
device_status = postgresql.ENUM(
    "online", "offline", "degraded", name="devicestatus", create_type=False
)
ota_status = postgresql.ENUM(
    "pending_approval",
    "scheduled",
    "in_progress",
    "completed",
    "failed",
    "rolled_back",
    name="otastatus",
    create_type=False,
)
ota_device_status = postgresql.ENUM(
    "pending",
    "in_progress",
    "completed",
    "failed",
    "rolled_back",
    name="otadevicestatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    device_status.create(bind, checkfirst=True)
    ota_status.create(bind, checkfirst=True)
    ota_device_status.create(bind, checkfirst=True)

    # --- edge_devices ---
    op.create_table(
        "edge_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("device_name", sa.String(200), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False),
        sa.Column("hardware_info", postgresql.JSON(), nullable=False),
        sa.Column("network_info", postgresql.JSON(), nullable=False),
        sa.Column("api_key", sa.String(100), nullable=False, unique=True),
        sa.Column("status", device_status, nullable=False, server_default="online"),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_edge_devices_api_key", "edge_devices", ["api_key"])
    op.create_index(
        "ix_edge_devices_workspace_status", "edge_devices", ["workspace_id", "status"]
    )

    # --- device_metrics ---
    op.create_table(
        "device_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("edge_devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSON(), nullable=False),
    )
    op.create_index(
        "ix_device_metrics_device_timestamp",
        "device_metrics",
        ["device_id", "timestamp"],
    )

    # --- ota_updates ---
    op.create_table(
        "ota_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("model_id", sa.String(200), nullable=False),
        sa.Column("previous_model_id", sa.String(200), nullable=True),
        sa.Column("strategy", sa.String(20), nullable=False, server_default="rolling"),
        sa.Column(
            "status", ota_status, nullable=False, server_default="pending_approval"
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ota_updates_workspace", "ota_updates", ["workspace_id"])

    # --- ota_device_rollouts ---
    op.create_table(
        "ota_device_rollouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "update_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ota_updates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status", ota_device_status, nullable=False, server_default="pending"
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_ota_device_rollouts_update", "ota_device_rollouts", ["update_id"]
    )

    # --- device_configs ---
    op.create_table(
        "device_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("edge_devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("config_version", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSON(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "device_id", "config_version", name="uq_device_config_version"
        ),
    )
    op.create_index("ix_device_configs_device", "device_configs", ["device_id"])

    # --- offline_packages ---
    op.create_table(
        "offline_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=True,
        ),
        sa.Column("model_id", sa.String(200), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False),
        sa.Column("model_format", sa.String(50), nullable=False),
        sa.Column("size_mb", sa.Float(), nullable=False, server_default="0"),
        sa.Column("contents", postgresql.JSON(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_offline_packages_workspace", "offline_packages", ["workspace_id"]
    )

    # --- sync_plans ---
    op.create_table(
        "sync_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("edge_devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_id", sa.String(200), nullable=False),
        sa.Column("model_size_mb", sa.Float(), nullable=False, server_default="0"),
        sa.Column("effective_size_mb", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "available_bandwidth_mbps", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("estimated_time", sa.String(50), nullable=False, server_default=""),
        sa.Column("strategy", sa.String(20), nullable=False, server_default="full"),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("progress_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("transferred_mb", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_sync_plans_device", "sync_plans", ["device_id"])


def downgrade() -> None:
    op.drop_table("sync_plans")
    op.drop_table("offline_packages")
    op.drop_table("device_configs")
    op.drop_table("ota_device_rollouts")
    op.drop_table("ota_updates")
    op.drop_table("device_metrics")
    op.drop_table("edge_devices")

    bind = op.get_bind()
    ota_device_status.drop(bind, checkfirst=True)
    ota_status.drop(bind, checkfirst=True)
    device_status.drop(bind, checkfirst=True)
