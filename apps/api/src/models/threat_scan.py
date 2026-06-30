"""ORM models for threat scan results stored in the SaaS database."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ThreatScan(Base):
    __tablename__ = "threat_scans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    appliance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appliances.id"), nullable=False)
    scan_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hosts_scanned: Mapped[int] = mapped_column(Integer, default=1)
    signatures_checked: Mapped[int] = mapped_column(Integer, default=0)
    yara_rules_checked: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    findings: Mapped[list[ThreatFinding]] = relationship(
        back_populates="scan", cascade="all, delete-orphan"
    )


class ThreatFinding(Base):
    __tablename__ = "threat_findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("threat_scans.id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    signature_id: Mapped[str] = mapped_column(String(255), nullable=False)
    threat_name: Mapped[str] = mapped_column(String(255), nullable=False)
    threat_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    indicator_type: Mapped[str] = mapped_column(String(50), nullable=False)
    indicator_value: Mapped[str] = mapped_column(String(1024), nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    mitre_technique: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, investigating, resolved
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan: Mapped[ThreatScan] = relationship(back_populates="findings")


class ThreatIncident(Base):
    __tablename__ = "threat_incidents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    incident_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, contained, resolved
    affected_host: Mapped[str] = mapped_column(String(255), nullable=False)
    threat_name: Mapped[str] = mapped_column(String(255), nullable=False)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("threat_findings.id"))
    # IR workflow state
    backup_triggered: Mapped[bool] = mapped_column(default=False)
    backup_job_id: Mapped[str | None] = mapped_column(String(255))
    soar_dispatched: Mapped[bool] = mapped_column(default=False)
    soar_incident_id: Mapped[str | None] = mapped_column(String(255))
    siem_dispatched: Mapped[bool] = mapped_column(default=False)
    veeamone_reported: Mapped[bool] = mapped_column(default=False)
    notifications_sent: Mapped[bool] = mapped_column(default=False)
    ir_log: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
