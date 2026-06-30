"""add notification_channels table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("destination", sa.String(512), nullable=False),
        sa.Column("events", postgresql.JSONB, server_default="[]"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notification_channels_org", "notification_channels", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_channels_org")
    op.drop_table("notification_channels")
