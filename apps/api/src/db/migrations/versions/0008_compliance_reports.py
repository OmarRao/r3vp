"""compliance_reports table

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("from_date", sa.String(10), nullable=False),
        sa.Column("to_date", sa.String(10), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="generating"),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("storage_path", sa.String(512), nullable=True),
        sa.Column("summary", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_compliance_reports_org_id", "compliance_reports", ["org_id"])
    op.create_index("ix_compliance_reports_generated_at", "compliance_reports", ["generated_at"])


def downgrade() -> None:
    op.drop_table("compliance_reports")
