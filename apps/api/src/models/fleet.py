"""Fleet management: appliance groups, health snapshots, bulk config."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ApplianceGroup(Base):
    __tablename__ = "appliance_groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    site_name: Mapped[str | None] = mapped_column(String(200))
    # e.g. "NYC-DC1", "Azure-EastUS", "DR-Site"
    region: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    config_template: Mapped[dict] = mapped_column(JSONB, default=dict)
    # config pushed to all appliances in this group on sync
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class ApplianceGroupMember(Base):
    __tablename__ = "appliance_group_members"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appliance_groups.id", ondelete="CASCADE"), nullable=False)
    appliance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApplianceHealthSnapshot(Base):
    __tablename__ = "appliance_health_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    appliance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # healthy | degraded | offline | warning
    cpu_pct: Mapped[int | None] = mapped_column(Integer)
    memory_pct: Mapped[int | None] = mapped_column(Integer)
    disk_pct: Mapped[int | None] = mapped_column(Integer)
    veeam_connected: Mapped[bool] = mapped_column(Boolean, default=True)
    vcenter_connected: Mapped[bool] = mapped_column(Boolean, default=True)
    temporal_connected: Mapped[bool] = mapped_column(Boolean, default=True)
    workload_count: Mapped[int] = mapped_column(Integer, default=0)
    last_test_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[str | None] = mapped_column(String(20))
    uptime_hours: Mapped[int | None] = mapped_column(Integer)
    alerts: Mapped[list] = mapped_column(JSONB, default=list)
    # list of {"level": "warning|error", "message": "..."}
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BulkConfigJob(Base):
    __tablename__ = "bulk_config_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appliance_groups.id"))
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    target_appliance_ids: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | running | completed | partial | failed
    results: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"appliance_id": "...", "status": "ok|error", "error": "..."}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
