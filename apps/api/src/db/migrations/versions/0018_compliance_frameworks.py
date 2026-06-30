"""Custom compliance frameworks, controls, assessments

Revision ID: 0018
Revises: 0017
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_frameworks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("short_code", sa.String(30), nullable=False),
        sa.Column("version", sa.String(20), nullable=True),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("is_builtin", sa.Boolean, server_default="false"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_compliance_frameworks_org_id", "compliance_frameworks", ["org_id"])

    op.create_table(
        "compliance_controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("framework_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("control_id", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("r3vp_evidence_types", postgresql.JSONB, server_default="[]"),
        sa.Column("r3vp_metric", sa.String(100), nullable=True),
        sa.Column("pass_threshold", sa.Integer, nullable=True),
        sa.Column("weight", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_compliance_controls_framework_id", "compliance_controls", ["framework_id"])

    op.create_table(
        "framework_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("framework_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.String(10), nullable=False),
        sa.Column("period_end", sa.String(10), nullable=False),
        sa.Column("overall_score", sa.Integer, nullable=False),
        sa.Column("controls_assessed", sa.Integer, server_default="0"),
        sa.Column("controls_passing", sa.Integer, server_default="0"),
        sa.Column("control_results", postgresql.JSONB, server_default="{}"),
        sa.Column("pdf_path", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_framework_assessments_org_id", "framework_assessments", ["org_id"])


def downgrade() -> None:
    op.drop_table("framework_assessments")
    op.drop_table("compliance_controls")
    op.drop_table("compliance_frameworks")
