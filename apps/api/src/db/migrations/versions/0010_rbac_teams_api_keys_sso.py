"""RBAC: roles, org_members, org_invites, api_keys, sso_configs tables

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), server_default=""),
        sa.Column("permissions", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("is_system", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("org_id", "name", name="uq_roles_org_name"),
    )

    op.create_table(
        "org_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_members_org_user"),
    )
    op.create_index("ix_org_members_org_id", "org_members", ["org_id"])

    op.create_table(
        "org_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_org_invites_org_id", "org_invites", ["org_id"])
    op.create_index("ix_org_invites_token", "org_invites", ["token"])

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("scopes", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked", sa.Boolean, server_default="false"),
    )
    op.create_index("ix_api_keys_org_id", "api_keys", ["org_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    op.create_table(
        "sso_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(512), nullable=False),
        sa.Column("sso_url", sa.String(512), nullable=False),
        sa.Column("certificate", sa.String(8192), nullable=False),
        sa.Column("attribute_mapping", postgresql.JSONB, server_default="'{}'"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed built-in system roles with no org_id
    op.execute("""
        INSERT INTO roles (id, org_id, name, description, permissions, is_system) VALUES
        (gen_random_uuid(), NULL, 'owner',    'Full access including SSO configuration',       '["workloads:read","workloads:write","workloads:delete","test_runs:read","test_runs:trigger","reports:read","reports:generate","reports:schedule","evidence:read","threats:read","incidents:read","incidents:write","audit:read","team:read","team:invite","team:manage","api_keys:read","api_keys:write","appliances:read","appliances:manage","settings:read","settings:write","sso:manage"]', true),
        (gen_random_uuid(), NULL, 'admin',    'Full access except SSO configuration',          '["workloads:read","workloads:write","workloads:delete","test_runs:read","test_runs:trigger","reports:read","reports:generate","reports:schedule","evidence:read","threats:read","incidents:read","incidents:write","audit:read","team:read","team:invite","team:manage","api_keys:read","api_keys:write","appliances:read","appliances:manage","settings:read","settings:write"]', true),
        (gen_random_uuid(), NULL, 'operator', 'Manage workloads, run tests, manage appliances','["workloads:read","workloads:write","test_runs:read","test_runs:trigger","reports:read","evidence:read","threats:read","incidents:read","incidents:write","audit:read","appliances:read","appliances:manage","team:read","settings:read"]', true),
        (gen_random_uuid(), NULL, 'auditor',  'Read reports and audit log, generate PDFs',     '["workloads:read","test_runs:read","reports:read","reports:generate","evidence:read","threats:read","incidents:read","audit:read","team:read"]', true),
        (gen_random_uuid(), NULL, 'viewer',   'Read-only access to all views',                 '["workloads:read","test_runs:read","reports:read","threats:read","incidents:read","team:read"]', true)
    """)


def downgrade() -> None:
    op.drop_table("sso_configs")
    op.drop_table("api_keys")
    op.drop_table("org_invites")
    op.drop_table("org_members")
    op.drop_table("roles")
