"""
Threat intelligence API endpoints.

Appliances submit scan results here. Portal queries findings and incidents.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy -- https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser, AdminUser, CurrentUser
from src.db.session import get_db
from src.models.threat_scan import ThreatFinding, ThreatIncident, ThreatScan
from src.models.appliance import Appliance

router = APIRouter(prefix="/v1/threat-intel", tags=["threat-intel"])


class ScanFindingIn(BaseModel):
    signature_id: str
    threat_name: str
    threat_type: str
    severity: str
    host: str
    indicator_type: str
    indicator_value: str
    context: dict = {}
    mitre_technique: str | None = None
    detected_at: datetime


class ScanResultIn(BaseModel):
    scan_id: str
    appliance_id: str
    started_at: datetime
    completed_at: datetime
    hosts_scanned: int = 1
    signatures_checked: int = 0
    yara_rules_checked: int = 0
    findings: list[ScanFindingIn] = []
    error: str | None = None


@router.post("/scans", status_code=201)
async def submit_scan_result(
    payload: ScanResultIn,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Called by the appliance to submit threat scan results.
    Uses appliance_id from the payload (authenticated via mTLS at the gateway level).
    """
    appliance_id = uuid.UUID(payload.appliance_id)

    # Look up org_id from the appliance
    appliance = await db.scalar(select(Appliance).where(Appliance.id == appliance_id))
    if not appliance:
        raise HTTPException(status_code=404, detail="Appliance not found")
    org_id = appliance.org_id

    # Count by severity
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in payload.findings:
        sev = f.severity.lower()
        if sev in sev_counts:
            sev_counts[sev] += 1

    scan = ThreatScan(
        id=uuid.uuid4(),
        org_id=org_id,
        appliance_id=appliance_id,
        scan_id=payload.scan_id,
        started_at=payload.started_at,
        completed_at=payload.completed_at,
        hosts_scanned=payload.hosts_scanned,
        signatures_checked=payload.signatures_checked,
        yara_rules_checked=payload.yara_rules_checked,
        critical_count=sev_counts["critical"],
        high_count=sev_counts["high"],
        medium_count=sev_counts["medium"],
        low_count=sev_counts["low"],
        error=payload.error,
    )
    db.add(scan)
    await db.flush()

    critical_findings: list[ThreatFinding] = []
    for f in payload.findings:
        finding = ThreatFinding(
            id=uuid.uuid4(),
            scan_id=scan.id,
            org_id=org_id,
            signature_id=f.signature_id,
            threat_name=f.threat_name,
            threat_type=f.threat_type,
            severity=f.severity,
            host=f.host,
            indicator_type=f.indicator_type,
            indicator_value=f.indicator_value,
            context=f.context,
            mitre_technique=f.mitre_technique,
            detected_at=f.detected_at,
        )
        db.add(finding)
        if f.severity.lower() in ("critical", "high"):
            critical_findings.append(finding)

    await db.commit()

    # Trigger incident response for critical/high findings
    from src.services.notification_config import get_org_integration_configs
    for finding in critical_findings:
        try:
            configs = await get_org_integration_configs(db, org_id)
            from src.services.incident_response import handle_threat_finding
            await handle_threat_finding(
                db, finding, org_id,
                soar_config=configs.get("soar"),
                siem_config=configs.get("siem"),
                veeamone_config=configs.get("veeamone"),
                notification_channels=configs.get("channels", []),
            )
        except Exception as exc:
            import structlog as _sl
            _sl.get_logger().warning("ir.auto_trigger.failed", error=str(exc))

    return {
        "scan_id": payload.scan_id,
        "findings": len(payload.findings),
        "critical": sev_counts["critical"],
        "incidents_created": len(critical_findings),
    }


@router.get("/findings")
async def list_findings(
    user: CurrentUser = Depends(AuthUser),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List threat findings for the authenticated org."""
    q = select(ThreatFinding).where(ThreatFinding.org_id == user.org_id)
    if status:
        q = q.where(ThreatFinding.status == status)
    if severity:
        q = q.where(ThreatFinding.severity == severity)
    q = q.order_by(ThreatFinding.detected_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id),
            "threat_name": r.threat_name,
            "threat_type": r.threat_type,
            "severity": r.severity,
            "host": r.host,
            "indicator_type": r.indicator_type,
            "indicator_value": r.indicator_value,
            "mitre_technique": r.mitre_technique,
            "status": r.status,
            "detected_at": r.detected_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/incidents")
async def list_incidents(
    user: CurrentUser = Depends(AuthUser),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
) -> list[dict]:
    """List incidents for the authenticated org."""
    q = select(ThreatIncident).where(ThreatIncident.org_id == user.org_id)
    if status:
        q = q.where(ThreatIncident.status == status)
    q = q.order_by(ThreatIncident.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id),
            "incident_number": r.incident_number,
            "title": r.title,
            "severity": r.severity,
            "status": r.status,
            "affected_host": r.affected_host,
            "threat_name": r.threat_name,
            "backup_triggered": r.backup_triggered,
            "soar_dispatched": r.soar_dispatched,
            "siem_dispatched": r.siem_dispatched,
            "veeamone_reported": r.veeamone_reported,
            "ir_log": r.ir_log,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/incidents/{incident_id}")
async def get_incident(
    incident_id: uuid.UUID,
    user: CurrentUser = Depends(AuthUser),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single incident with full IR log."""
    incident = await db.scalar(
        select(ThreatIncident).where(
            ThreatIncident.id == incident_id,
            ThreatIncident.org_id == user.org_id,
        )
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "id": str(incident.id),
        "incident_number": incident.incident_number,
        "title": incident.title,
        "severity": incident.severity,
        "status": incident.status,
        "affected_host": incident.affected_host,
        "threat_name": incident.threat_name,
        "backup_triggered": incident.backup_triggered,
        "backup_job_id": incident.backup_job_id,
        "soar_dispatched": incident.soar_dispatched,
        "soar_incident_id": incident.soar_incident_id,
        "siem_dispatched": incident.siem_dispatched,
        "veeamone_reported": incident.veeamone_reported,
        "notifications_sent": incident.notifications_sent,
        "ir_log": incident.ir_log,
        "created_at": incident.created_at.isoformat(),
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
    }


@router.patch("/incidents/{incident_id}/resolve")
async def resolve_incident(
    incident_id: uuid.UUID,
    user: CurrentUser = Depends(AdminUser),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark an incident as resolved."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(ThreatIncident)
        .where(
            ThreatIncident.id == incident_id,
            ThreatIncident.org_id == user.org_id,
        )
        .values(status="resolved", resolved_at=now)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    await db.commit()
    return {"status": "resolved"}


@router.get("/scans")
async def list_scans(
    user: CurrentUser = Depends(AuthUser),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[dict]:
    """List recent threat scans for the authenticated org."""
    rows = (await db.execute(
        select(ThreatScan)
        .where(ThreatScan.org_id == user.org_id)
        .order_by(ThreatScan.completed_at.desc())
        .limit(limit)
    )).scalars().all()
    return [
        {
            "id": str(r.id),
            "scan_id": r.scan_id,
            "started_at": r.started_at.isoformat(),
            "completed_at": r.completed_at.isoformat(),
            "hosts_scanned": r.hosts_scanned,
            "signatures_checked": r.signatures_checked,
            "critical_count": r.critical_count,
            "high_count": r.high_count,
            "medium_count": r.medium_count,
            "low_count": r.low_count,
        }
        for r in rows
    ]
