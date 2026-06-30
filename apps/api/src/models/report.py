"""Persisted compliance report records."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # report_type values: "soc2", "iso27001", "nist_csf", "monthly_summary", "cyber_insurance"
    from_date: Mapped[str] = mapped_column(String(10), nullable=False)   # YYYY-MM-DD
    to_date: Mapped[str] = mapped_column(String(10), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="generating")
    # status values: generating, ready, failed
    sha256: Mapped[str | None] = mapped_column(String(64))  # hex digest of PDF bytes
    storage_path: Mapped[str | None] = mapped_column(String(512))
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    # summary stores: total_runs, pass_rate_pct, rto_compliance_pct, controls_passing
