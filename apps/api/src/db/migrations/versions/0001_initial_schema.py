"""Initial schema: orgs, appliances, users, workloads, test_runs, test_run_steps,
health_check_results, audit_events.

Revision ID: 0001
Revises:
Create Date: 2026-06-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orgs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "appliances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50)),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True)),
        sa.Column("mtls_thumbprint", sa.String(512), nullable=False),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_appliances_org_id", "appliances", ["org_id"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("auth0_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("uq_users_auth0_sub", "users", ["auth0_sub"], unique=True)

    op.create_table(
        "workloads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("appliance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("os_type", sa.String(50)),
        sa.Column("ip_address", sa.String(50)),
        sa.Column("veeam_object_id", sa.String(255)),
        sa.Column("vcenter_moref", sa.String(255)),
        sa.Column("is_protected", sa.Boolean, server_default="false"),
        sa.Column("last_backup_at", sa.DateTime(timezone=True)),
        sa.Column("rto_target_mins", sa.Integer),
        sa.Column("rpo_target_mins", sa.Integer),
        sa.Column("tags", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_workloads_appliance_id", "workloads", ["appliance_id"])
    # Unique constraint used by ON CONFLICT in inventory upsert
    op.create_index(
        "uq_workloads_appliance_veeam", "workloads",
        ["appliance_id", "veeam_object_id"], unique=True,
        postgresql_where=sa.text("veeam_object_id IS NOT NULL"),
    )

    op.create_table(
        "test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workload_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workloads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("restore_point", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("rto_actual_mins", sa.Integer),
        sa.Column("rpo_actual_mins", sa.Integer),
        sa.Column("readiness_score", sa.Integer,
                  sa.CheckConstraint("readiness_score BETWEEN 0 AND 100")),
        sa.Column("failure_reason", sa.Text),
        sa.Column("evidence_path", sa.String(512)),
        sa.Column("workflow_run_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_test_runs_workload_id", "test_runs", ["workload_id"])
    op.create_index("ix_test_runs_status", "test_runs", ["status"])

    op.create_table(
        "test_run_steps",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("detail", postgresql.JSONB, server_default="{}"),
    )
    op.create_index("ix_test_run_steps_run_id", "test_run_steps", ["run_id"])

    op.create_table(
        "health_check_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("check_name", sa.String(100), nullable=False),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("output", sa.Text),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_health_check_results_run_id", "health_check_results", ["run_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("detail", postgresql.JSONB, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_org_id", "audit_events", ["org_id"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("health_check_results")
    op.drop_table("test_run_steps")
    op.drop_table("test_runs")
    op.drop_table("workloads")
    op.drop_table("users")
    op.drop_table("appliances")
    op.drop_table("orgs")
