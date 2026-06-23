"""Executive report and digest schedule models."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class DigestSchedule(Base):
    __tablename__ = "digest_schedules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    cadence: Mapped[str] = mapped_column(String(20), nullable=False)
    # weekly | monthly | quarterly
    recipients: Mapped[list] = mapped_column(JSONB, default=list)
    include_scorecard: Mapped[bool] = mapped_column(Boolean, default=True)
    include_trend_chart: Mapped[bool] = mapped_column(Boolean, default=True)
    include_provider_breakdown: Mapped[bool] = mapped_column(Boolean, default=True)
    include_top_risks: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class ScorecardSnapshot(Base):
    __tablename__ = "scorecard_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    snapshot_date: Mapped[str] = mapped_column(String(10), nullable=False)
    # YYYY-MM-DD of the snapshot
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    # 0-100
    workloads_total: Mapped[int] = mapped_column(Integer, default=0)
    workloads_tested: Mapped[int] = mapped_column(Integer, default=0)
    workloads_passing: Mapped[int] = mapped_column(Integer, default=0)
    rto_compliance_pct: Mapped[int] = mapped_column(Integer, default=0)
    active_threats: Mapped[int] = mapped_column(Integer, default=0)
    open_incidents: Mapped[int] = mapped_column(Integer, default=0)
    provider_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    top_risks: Mapped[list] = mapped_column(JSONB, default=list)
    # list of {"workload": str, "reason": str, "severity": "high|medium"}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
