"""Custom compliance framework and control mapping models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ComplianceFramework(Base):
    __tablename__ = "compliance_frameworks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_code: Mapped[str] = mapped_column(String(30), nullable=False)
    # e.g. PCI-DSS-4, HIPAA, DORA, MAS-TRM
    version: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(1000))
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    # True for SOC2/ISO27001/NIST CSF built-ins
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class ComplianceControl(Base):
    __tablename__ = "compliance_controls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    framework_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "Req 12.3.4", "Article 11(b)", "§ 164.308(a)(7)"
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    category: Mapped[str | None] = mapped_column(String(100))
    # e.g. "Backup and Recovery", "Business Continuity", "Incident Response"
    r3vp_evidence_types: Mapped[list] = mapped_column(JSONB, default=list)
    # which R3VP artifacts satisfy this control:
    # ["test_run_pass", "rto_measurement", "health_check", "audit_chain", "evidence_bundle"]
    r3vp_metric: Mapped[str | None] = mapped_column(String(100))
    # the specific metric this maps to: "pass_rate", "rto_compliance", "coverage_pct"
    pass_threshold: Mapped[int | None] = mapped_column(Integer)
    # e.g. pass_rate >= 95, coverage_pct >= 100
    weight: Mapped[int] = mapped_column(Integer, default=1)
    # relative weight for overall score calculation
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FrameworkAssessment(Base):
    __tablename__ = "framework_assessments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    framework_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    period_start: Mapped[str] = mapped_column(String(10), nullable=False)
    period_end: Mapped[str] = mapped_column(String(10), nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    # 0-100
    controls_assessed: Mapped[int] = mapped_column(Integer, default=0)
    controls_passing: Mapped[int] = mapped_column(Integer, default=0)
    control_results: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {control_id: {"status": "pass|fail|na", "evidence": [...], "score": int}}
    pdf_path: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
