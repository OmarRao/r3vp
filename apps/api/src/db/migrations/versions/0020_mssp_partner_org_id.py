"""Add org_id to mssp_partners so a partner is tied to its operating org

Revision ID: 0020
Revises: 0019
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable at the DB level to tolerate any pre-existing partner rows; the
    # ORM model treats it as required and the provisioning helper always sets
    # it, so new rows are always populated.
    op.add_column(
        "mssp_partners",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_mssp_partners_org_id", "mssp_partners", ["org_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_mssp_partners_org_id", "mssp_partners", type_="unique")
    op.drop_column("mssp_partners", "org_id")
