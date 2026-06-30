"""MSSP multi-org management models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MsspPartner(Base):
    __tablename__ = "mssp_partners"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(512))
    primary_color: Mapped[str | None] = mapped_column(String(7))
    # hex color for white-label branding, e.g. #00B336
    contact_email: Mapped[str | None] = mapped_column(String(200))
    plan: Mapped[str] = mapped_column(String(50), default="mssp")
    max_customer_orgs: Mapped[int] = mapped_column(Integer, default=50)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MsspCustomerOrg(Base):
    __tablename__ = "mssp_customer_orgs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mssp_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mssp_partners.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100))
    tier: Mapped[str] = mapped_column(String(50), default="standard")
    # standard | premium | enterprise
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    notes: Mapped[str | None] = mapped_column(String(1000))
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MsspAlertRule(Base):
    __tablename__ = "mssp_alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mssp_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mssp_partners.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    # readiness_below | rto_breach | test_failure | no_test_in_days | threat_detected
    threshold: Mapped[int | None] = mapped_column(Integer)
    applies_to: Mapped[str] = mapped_column(String(20), default="all")
    # all | tier:premium | tag:critical
    notification_channel: Mapped[str] = mapped_column(String(20), default="email")
    notification_target: Mapped[str | None] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
