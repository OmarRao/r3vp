"""report_schedules table and evidence_bundles table

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("cron", sa.String(100), nullable=False),
        sa.Column("period_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("recipients", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_report_schedules_org_id", "report_schedules", ["org_id"])

    op.create_table(
        "evidence_bundles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_reports.id"), nullable=True),
        sa.Column("from_date", sa.String(10), nullable=False),
        sa.Column("to_date", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("file_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("size_bytes", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_evidence_bundles_org_id", "evidence_bundles", ["org_id"])


def downgrade() -> None:
    op.drop_table("evidence_bundles")
    op.drop_table("report_schedules")
