"""Onboarding session tracking for new organizations."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class OnboardingSession(Base):
    __tablename__ = "onboarding_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(unique=True, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    # 1=org_profile, 2=deploy_appliance, 3=connect_veeam, 4=discover_workloads, 5=first_test, 6=complete
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    step_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    # stores per-step results: appliance_id, workload_count, first_test_run_id, etc.
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
