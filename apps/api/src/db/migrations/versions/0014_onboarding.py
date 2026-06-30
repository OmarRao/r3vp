"""onboarding_sessions table

Revision ID: 0014
Revises: 0013
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("current_step", sa.Integer, server_default="1"),
        sa.Column("completed", sa.Boolean, server_default="false"),
        sa.Column("dismissed", sa.Boolean, server_default="false"),
        sa.Column("step_data", postgresql.JSONB, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_onboarding_sessions_org_id", "onboarding_sessions", ["org_id"])


def downgrade() -> None:
    op.drop_table("onboarding_sessions")
