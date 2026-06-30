"""digest_schedules and scorecard_snapshots tables

Revision ID: 0011
Revises: 0010
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "digest_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cadence", sa.String(20), nullable=False),
        sa.Column("recipients", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("include_scorecard", sa.Boolean, server_default="true"),
        sa.Column("include_trend_chart", sa.Boolean, server_default="true"),
        sa.Column("include_provider_breakdown", sa.Boolean, server_default="true"),
        sa.Column("include_top_risks", sa.Boolean, server_default="true"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_digest_schedules_org_id", "digest_schedules", ["org_id"])

    op.create_table(
        "scorecard_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_date", sa.String(10), nullable=False),
        sa.Column("overall_score", sa.Integer, nullable=False),
        sa.Column("workloads_total", sa.Integer, server_default="0"),
        sa.Column("workloads_tested", sa.Integer, server_default="0"),
        sa.Column("workloads_passing", sa.Integer, server_default="0"),
        sa.Column("rto_compliance_pct", sa.Integer, server_default="0"),
        sa.Column("active_threats", sa.Integer, server_default="0"),
        sa.Column("open_incidents", sa.Integer, server_default="0"),
        sa.Column("provider_breakdown", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("top_risks", postgresql.JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scorecard_snapshots_org_id", "scorecard_snapshots", ["org_id"])
    op.create_index("ix_scorecard_snapshots_date", "scorecard_snapshots", ["org_id", "snapshot_date"])


def downgrade() -> None:
    op.drop_table("scorecard_snapshots")
    op.drop_table("digest_schedules")
