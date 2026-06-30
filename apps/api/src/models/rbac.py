"""RBAC models: roles, permissions, team memberships, and API keys."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    # null org_id = built-in system role
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # owner | admin | operator | auditor | viewer
    description: Mapped[str] = mapped_column(String(255), default="")
    permissions: Mapped[list] = mapped_column(JSONB, default=list)
    # list of permission strings e.g. ["workloads:read", "test_runs:trigger", ...]
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_roles_org_name"),)


class OrgMember(Base):
    """Maps a user to an org with a specific role."""
    __tablename__ = "org_members"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_org_members_org_user"),)


class OrgInvite(Base):
    """Pending invitations to join an org."""
    __tablename__ = "org_invites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(48)


class ApiKey(Base):
    """Service account API keys for programmatic access."""
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    # first 8 chars shown in UI for identification
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # SHA-256 of the full key; never stored in plaintext
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    # list of permission strings this key is allowed to use
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    @staticmethod
    def generate() -> tuple[str, str, str]:
        """Returns (full_key, prefix, sha256_hash)."""
        raw = "r3vp_" + secrets.token_urlsafe(40)
        prefix = raw[:12]
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return raw, prefix, digest

    @staticmethod
    def hash(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()


class SsoConfig(Base):
    """SAML 2.0 SSO configuration per org."""
    __tablename__ = "sso_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    # okta | azure_ad | google | ping | generic_saml
    entity_id: Mapped[str] = mapped_column(String(512), nullable=False)
    sso_url: Mapped[str] = mapped_column(String(512), nullable=False)
    certificate: Mapped[str] = mapped_column(String(8192), nullable=False)
    # PEM-encoded IdP signing certificate
    attribute_mapping: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"email": "...", "first_name": "...", "role": "..."}
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
