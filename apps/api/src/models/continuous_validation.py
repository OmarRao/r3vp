"""Continuous validation mode: policies, micro-validation checks, and result records."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ContinuousValidationPolicy(Base):
    __tablename__ = "continuous_validation_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    check_interval_mins: Mapped[int] = mapped_column(Integer, default=15)
    # how often to run micro-checks (default: every 15 minutes)
    workload_scope: Mapped[str] = mapped_column(String(20), default="all")
    # all | tier:critical | tag:production | specific
    workload_ids: Mapped[list] = mapped_column(JSONB, default=list)
    # only used when scope = "specific"
    checks_enabled: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"restore_point_freshness": true, "mount_check": true, "veeam_job_status": true, "agent_heartbeat": true}
    alert_on_failure: Mapped[bool] = mapped_column(Boolean, default=True)
    consecutive_failures_before_alert: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class MicroValidationRun(Base):
    __tablename__ = "micro_validation_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("continuous_validation_policies.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    workload_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workloads.id"))
    workload_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # pass | fail | warn | skipped
    checks_run: Mapped[int] = mapped_column(Integer, default=0)
    checks_passed: Mapped[int] = mapped_column(Integer, default=0)
    check_results: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"restore_point_freshness": {"status": "pass", "detail": "Latest RP: 2h ago", "value_hours": 2},
    #  "mount_check": {"status": "fail", "detail": "Mount endpoint unreachable"},
    #  "veeam_job_status": {"status": "pass", "detail": "Last job: Success"}}
    restore_point_age_hours: Mapped[int | None] = mapped_column(Integer)
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class ValidationAlert(Base):
    __tablename__ = "validation_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("continuous_validation_policies.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    workload_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    workload_name: Mapped[str | None] = mapped_column(String(200))
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # check_failure | restore_point_stale | veeam_job_failed | consecutive_failures
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    # critical | high | medium | low
    detail: Mapped[str] = mapped_column(String(1000), nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
