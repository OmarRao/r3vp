"""add role column to users

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(50), server_default="admin", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "role")
