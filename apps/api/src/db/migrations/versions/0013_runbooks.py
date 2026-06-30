"""DR runbook tables

Revision ID: 0013
Revises: 0012
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runbooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), server_default=""),
        sa.Column("scenario", sa.String(50), nullable=False),
        sa.Column("rto_target_mins", sa.Integer, nullable=True),
        sa.Column("tags", postgresql.JSONB, server_default="'[]'"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_execution_status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_runbooks_org_id", "runbooks", ["org_id"])

    op.create_table(
        "runbook_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runbook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("step_type", sa.String(50), nullable=False),
        sa.Column("workload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workloads.id"), nullable=True),
        sa.Column("depends_on_seq", postgresql.JSONB, server_default="'[]'"),
        sa.Column("parallel", sa.Boolean, server_default="false"),
        sa.Column("timeout_mins", sa.Integer, server_default="60"),
        sa.Column("config", postgresql.JSONB, server_default="'{}'"),
        sa.Column("on_failure", sa.String(20), server_default="stop"),
    )
    op.create_index("ix_runbook_steps_runbook_id", "runbook_steps", ["runbook_id"])

    op.create_table(
        "runbook_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runbook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runbooks.id"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("trigger_reason", sa.String(200), server_default="manual"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_rto_mins", sa.Integer, nullable=True),
        sa.Column("target_rto_mins", sa.Integer, nullable=True),
        sa.Column("rto_met", sa.Boolean, nullable=True),
        sa.Column("summary", postgresql.JSONB, server_default="'{}'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_runbook_executions_org_id", "runbook_executions", ["org_id"])
    op.create_index("ix_runbook_executions_runbook_id", "runbook_executions", ["runbook_id"])

    op.create_table(
        "runbook_execution_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runbook_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runbook_steps.id"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("step_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_secs", sa.Integer, nullable=True),
        sa.Column("output", postgresql.JSONB, server_default="'{}'"),
        sa.Column("error", sa.String(2000), nullable=True),
    )
    op.create_index("ix_runbook_execution_steps_execution_id", "runbook_execution_steps", ["execution_id"])


def downgrade() -> None:
    op.drop_table("runbook_execution_steps")
    op.drop_table("runbook_executions")
    op.drop_table("runbook_steps")
    op.drop_table("runbooks")
