"""integrations and integration_event_logs tables

Revision ID: 0012
Revises: 0011
"""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("trigger_events", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_integrations_org_id", "integrations", ["org_id"])

    op.create_table(
        "integration_event_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("integrations.id"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", postgresql.JSONB, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_detail", sa.String(1000), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("response_ms", sa.Integer, nullable=True),
    )
    op.create_index("ix_integration_event_logs_integration_id", "integration_event_logs", ["integration_id"])


def downgrade() -> None:
    op.drop_table("integration_event_logs")
    op.drop_table("integrations")
