"""Add provider, cloud_resource_id, cloud_region to workloads table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workloads", sa.Column("provider", sa.String(50), server_default="vmware", nullable=False))
    op.add_column("workloads", sa.Column("cloud_resource_id", sa.String(512), nullable=True))
    op.add_column("workloads", sa.Column("cloud_region", sa.String(100), nullable=True))
    op.create_index("ix_workloads_provider", "workloads", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_workloads_provider", "workloads")
    op.drop_column("workloads", "cloud_region")
    op.drop_column("workloads", "cloud_resource_id")
    op.drop_column("workloads", "provider")
