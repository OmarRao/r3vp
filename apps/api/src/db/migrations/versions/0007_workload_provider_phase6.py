"""Add provider_region and provider_cluster to workloads for Phase 6 hypervisors.

Adds two nullable string columns to support the expanded hypervisor roster:
- provider_cluster: Nutanix cluster_uuid, Proxmox node name, RHV cluster_id,
  XenServer pool UUID, Sangfor cluster ID, GCP project/zone composite.
- provider_region is already covered by cloud_region (added in 0006); this
  migration adds only provider_cluster which is the missing piece.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-17

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workloads", sa.Column("provider_cluster", sa.String(200), nullable=True))
    # Index supports per-cluster workload queries across all hypervisor types
    op.create_index("ix_workloads_provider_cluster", "workloads", ["provider_cluster"])


def downgrade() -> None:
    op.drop_index("ix_workloads_provider_cluster", table_name="workloads")
    op.drop_column("workloads", "provider_cluster")
