"""MSSP partner, customer orgs, alert rules tables

Revision ID: 0017
Revises: 0016
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mssp_partners",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("logo_url", sa.String(512), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=True),
        sa.Column("contact_email", sa.String(200), nullable=True),
        sa.Column("plan", sa.String(50), server_default="mssp"),
        sa.Column("max_customer_orgs", sa.Integer, server_default="50"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "mssp_customer_orgs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mssp_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mssp_partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("tier", sa.String(50), server_default="standard"),
        sa.Column("tags", postgresql.JSONB, server_default="[]"),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_mssp_customer_orgs_mssp_id", "mssp_customer_orgs", ["mssp_id"])

    op.create_table(
        "mssp_alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mssp_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mssp_partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("condition", sa.String(50), nullable=False),
        sa.Column("threshold", sa.Integer, nullable=True),
        sa.Column("applies_to", sa.String(20), server_default="all"),
        sa.Column("notification_channel", sa.String(20), server_default="email"),
        sa.Column("notification_target", sa.String(500), nullable=True),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_mssp_alert_rules_mssp_id", "mssp_alert_rules", ["mssp_id"])


def downgrade() -> None:
    op.drop_table("mssp_alert_rules")
    op.drop_table("mssp_customer_orgs")
    op.drop_table("mssp_partners")
