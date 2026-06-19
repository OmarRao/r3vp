"""Scheduled compliance report delivery configuration."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # soc2 | iso27001 | nist_csf | monthly_summary | cyber_insurance
    cron: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. "0 8 1 * *" = 08:00 on 1st of every month
    period_days: Mapped[int] = mapped_column(default=30)
    # how many days back the report covers
    recipients: Mapped[list] = mapped_column(JSONB, default=list)
    # list of {"type": "email"|"slack"|"teams", "destination": "..."}
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
