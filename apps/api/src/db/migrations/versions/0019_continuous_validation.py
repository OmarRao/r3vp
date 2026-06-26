"""Continuous validation policies, micro-validation runs, validation alerts

Revision ID: 0019
Revises: 0018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "continuous_validation_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("check_interval_mins", sa.Integer, server_default="15"),
        sa.Column("workload_scope", sa.String(20), server_default="all"),
        sa.Column("workload_ids", postgresql.JSONB, server_default="[]"),
        sa.Column("checks_enabled", postgresql.JSONB, server_default="{}"),
        sa.Column("alert_on_failure", sa.Boolean, server_default="true"),
        sa.Column("consecutive_failures_before_alert", sa.Integer, server_default="2"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_cv_policies_org_id", "continuous_validation_policies", ["org_id"])

    op.create_table(
        "micro_validation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("continuous_validation_policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workloads.id"), nullable=True),
        sa.Column("workload_name", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("checks_run", sa.Integer, server_default="0"),
        sa.Column("checks_passed", sa.Integer, server_default="0"),
        sa.Column("check_results", postgresql.JSONB, server_default="{}"),
        sa.Column("restore_point_age_hours", sa.Integer, nullable=True),
        sa.Column("alert_sent", sa.Boolean, server_default="false"),
        sa.Column("ran_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("duration_ms", sa.Integer, nullable=True),
    )
    op.create_index("ix_micro_validation_runs_org_id", "micro_validation_runs", ["org_id"])
    op.create_index("ix_micro_validation_runs_policy_id", "micro_validation_runs", ["policy_id"])

    op.create_table(
        "validation_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("continuous_validation_policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workload_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workload_name", sa.String(200), nullable=True),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("detail", sa.String(1000), nullable=False),
        sa.Column("resolved", sa.Boolean, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_validation_alerts_org_id", "validation_alerts", ["org_id"])


def downgrade() -> None:
    op.drop_table("validation_alerts")
    op.drop_table("micro_validation_runs")
    op.drop_table("continuous_validation_policies")
