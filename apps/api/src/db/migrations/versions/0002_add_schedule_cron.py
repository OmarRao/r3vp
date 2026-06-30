"""add schedule_cron to workloads

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workloads", sa.Column("schedule_cron", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("workloads", "schedule_cron")
