"""Appliance fleet: groups, health snapshots, bulk config jobs

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "appliance_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), server_default=""),
        sa.Column("site_name", sa.String(200), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("tags", postgresql.JSONB, server_default="[]"),
        sa.Column("config_template", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_appliance_groups_org_id", "appliance_groups", ["org_id"])

    op.create_table(
        "appliance_group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appliance_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("appliance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_appliance_group_members_group_id", "appliance_group_members", ["group_id"])

    op.create_table(
        "appliance_health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("appliance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("cpu_pct", sa.Integer, nullable=True),
        sa.Column("memory_pct", sa.Integer, nullable=True),
        sa.Column("disk_pct", sa.Integer, nullable=True),
        sa.Column("veeam_connected", sa.Boolean, server_default="true"),
        sa.Column("vcenter_connected", sa.Boolean, server_default="true"),
        sa.Column("temporal_connected", sa.Boolean, server_default="true"),
        sa.Column("workload_count", sa.Integer, server_default="0"),
        sa.Column("last_test_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.String(20), nullable=True),
        sa.Column("uptime_hours", sa.Integer, nullable=True),
        sa.Column("alerts", postgresql.JSONB, server_default="[]"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_appliance_health_snapshots_appliance_id", "appliance_health_snapshots", ["appliance_id"])
    op.create_index("ix_appliance_health_snapshots_org_id", "appliance_health_snapshots", ["org_id"])

    op.create_table(
        "bulk_config_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appliance_groups.id"), nullable=True),
        sa.Column("config", postgresql.JSONB, server_default="{}"),
        sa.Column("target_appliance_ids", postgresql.JSONB, server_default="[]"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("results", postgresql.JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_bulk_config_jobs_org_id", "bulk_config_jobs", ["org_id"])


def downgrade() -> None:
    op.drop_table("bulk_config_jobs")
    op.drop_table("appliance_health_snapshots")
    op.drop_table("appliance_group_members")
    op.drop_table("appliance_groups")
