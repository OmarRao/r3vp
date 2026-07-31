# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Workload(Base):
    __tablename__ = "workloads"

    # Partial unique index used by the inventory-sync ON CONFLICT upsert.
    # Mirrors migration 0001 so create_all (tests) matches the migrated schema.
    __table_args__ = (
        Index(
            "uq_workloads_appliance_veeam",
            "appliance_id",
            "veeam_object_id",
            unique=True,
            postgresql_where=text("veeam_object_id IS NOT NULL"),
        ),
    )

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
    provider: Mapped[str] = mapped_column(String(50), default="vmware")
    # vmware | hyperv | azure | aws | proxmox | nutanix | rhv | xenserver | sangfor | gcp
    cloud_resource_id: Mapped[str | None] = mapped_column(String(512))   # ARN, Azure resource ID, Hyper-V VM ID
    cloud_region: Mapped[str | None] = mapped_column(String(100))         # Azure/AWS/GCP region
    provider_cluster: Mapped[str | None] = mapped_column(String(200))
    # Nutanix cluster_uuid, Proxmox node, RHV cluster_id, XenServer pool UUID, GCP project/zone
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    appliance: Mapped[object] = relationship("Appliance", back_populates="workloads")
    test_runs: Mapped[list] = relationship("TestRun", back_populates="workload")
