from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Workload(Base):
    __tablename__ = "workloads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    appliance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appliances.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # vmware | hyperv | physical
    os_type: Mapped[str | None] = mapped_column(String(50))             # windows | linux
    ip_address: Mapped[str | None] = mapped_column(String(50))
    veeam_object_id: Mapped[str | None] = mapped_column(String(255))
    vcenter_moref: Mapped[str | None] = mapped_column(String(255))
    is_protected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rto_target_mins: Mapped[int | None] = mapped_column(Integer)
    rpo_target_mins: Mapped[int | None] = mapped_column(Integer)
    schedule_cron: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    appliance: Mapped[object] = relationship("Appliance", back_populates="workloads")
    test_runs: Mapped[list] = relationship("TestRun", back_populates="workload")
