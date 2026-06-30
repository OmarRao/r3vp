"""DR Runbook models: playbooks, steps, executions."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Runbook(Base):
    __tablename__ = "runbooks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="")
    scenario: Mapped[str] = mapped_column(String(50), nullable=False)
    # ransomware | datacenter_failure | cloud_outage | site_failover | custom
    rto_target_mins: Mapped[int | None] = mapped_column(Integer)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_execution_status: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class RunbookStep(Base):
    __tablename__ = "runbook_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    runbook_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    # execution order, 1-based
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    step_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # recover_workload | health_check | notify | wait | manual_gate | run_script
    workload_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workloads.id"))
    depends_on_seq: Mapped[list] = mapped_column(JSONB, default=list)
    # list of seq numbers that must complete before this step starts
    parallel: Mapped[bool] = mapped_column(Boolean, default=False)
    # if True, run concurrently with other parallel steps at same dependency level
    timeout_mins: Mapped[int] = mapped_column(Integer, default=60)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    # step_type-specific config:
    # recover_workload: {"priority": 1, "isolated": true}
    # notify: {"channel": "slack", "destination": "...", "message": "..."}
    # wait: {"duration_mins": 5}
    # manual_gate: {"instructions": "Confirm DNS cutover complete"}
    # run_script: {"script": "...", "interpreter": "bash"}
    on_failure: Mapped[str] = mapped_column(String(20), default="stop")
    # stop | continue | rollback


class RunbookExecution(Base):
    __tablename__ = "runbook_executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    runbook_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runbooks.id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    trigger_reason: Mapped[str] = mapped_column(String(200), default="manual")
    # manual | incident_auto | scheduled
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | running | completed | failed | rolled_back | cancelled
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_rto_mins: Mapped[int | None] = mapped_column(Integer)
    target_rto_mins: Mapped[int | None] = mapped_column(Integer)
    rto_met: Mapped[bool | None] = mapped_column(Boolean)
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunbookExecutionStep(Base):
    __tablename__ = "runbook_execution_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runbook_executions.id", ondelete="CASCADE"), nullable=False)
    step_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runbook_steps.id"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    step_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | running | completed | failed | skipped | waiting_gate
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_secs: Mapped[int | None] = mapped_column(Integer)
    output: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000))
