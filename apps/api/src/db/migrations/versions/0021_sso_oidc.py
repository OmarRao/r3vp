"""Extend sso_configs for OIDC (protocol + oidc_* columns)

Adds OIDC support alongside the existing SAML columns. The SAML columns
(entity_id, sso_url, certificate) become nullable so an OIDC-only org can be
stored without dummy SAML values. A ``protocol`` discriminator column selects
which set of columns is authoritative for a given row.

Revision ID: 0021
Revises: 0020
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sso_configs",
        sa.Column("protocol", sa.String(10), nullable=False, server_default="saml"),
    )
    op.add_column("sso_configs", sa.Column("oidc_issuer", sa.String(512), nullable=True))
    op.add_column("sso_configs", sa.Column("oidc_client_id", sa.String(255), nullable=True))
    op.add_column("sso_configs", sa.Column("oidc_client_secret", sa.String(512), nullable=True))
    op.add_column("sso_configs", sa.Column("oidc_redirect_uri", sa.String(512), nullable=True))
    op.add_column(
        "sso_configs",
        sa.Column(
            "oidc_scopes",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # SAML columns are now optional (OIDC rows leave them null).
    op.alter_column("sso_configs", "entity_id", nullable=True)
    op.alter_column("sso_configs", "sso_url", nullable=True)
    op.alter_column("sso_configs", "certificate", nullable=True)


def downgrade() -> None:
    op.alter_column("sso_configs", "certificate", nullable=False)
    op.alter_column("sso_configs", "sso_url", nullable=False)
    op.alter_column("sso_configs", "entity_id", nullable=False)
    op.drop_column("sso_configs", "oidc_scopes")
    op.drop_column("sso_configs", "oidc_redirect_uri")
    op.drop_column("sso_configs", "oidc_client_secret")
    op.drop_column("sso_configs", "oidc_client_id")
    op.drop_column("sso_configs", "oidc_issuer")
    op.drop_column("sso_configs", "protocol")
