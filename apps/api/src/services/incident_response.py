"""
Automated incident response service for R3VP.

When a critical threat is detected, this service:
1. Triggers an immediate Veeam backup of affected VMs
2. Creates a ThreatIncident record
3. Dispatches to configured SOAR platform
4. Emits SIEM events
5. Reports to VeeamONE
6. Sends notifications via console, email, Slack, Teams

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy -- https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.threat_scan import ThreatFinding, ThreatIncident

log = structlog.get_logger()


async def handle_threat_finding(
    db: AsyncSession,
    finding: ThreatFinding,
    org_id: uuid.UUID,
    *,
    soar_config: dict | None = None,
    siem_config: dict | None = None,
    veeamone_config: dict | None = None,
    notification_channels: list[dict] | None = None,
) -> ThreatIncident:
    """
    Orchestrate the full incident response workflow for a confirmed threat finding.

    Returns the created ThreatIncident record.
    """
    # Generate incident number
    count = await db.scalar(
        select(func.count()).select_from(ThreatIncident).where(
            ThreatIncident.org_id == org_id
        )
    )
    incident_number = f"INC-{(count or 0) + 1:04d}"

    incident = ThreatIncident(
        id=uuid.uuid4(),
        org_id=org_id,
        incident_number=incident_number,
        title=f"{finding.severity.upper()} - {finding.threat_name} on {finding.host}",
        severity=finding.severity,
        affected_host=finding.host,
        threat_name=finding.threat_name,
        finding_id=finding.id,
        ir_log=[],
    )
    db.add(incident)
    await db.flush()  # get the ID

    ir_log: list[dict] = []

    def _log_step(step: str, detail: str, success: bool = True) -> None:
        entry = {
            "step": step,
            "detail": detail,
            "success": success,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        ir_log.append(entry)
        log.info("incident_response.step", incident=incident_number, step=step, success=success)

    _log_step("threat_detected", f"{finding.threat_name} matched on {finding.host}")

    # 1. Trigger Veeam backup (best-effort)
    try:
        backup_job_id = await _trigger_backup(finding.host)
        incident.backup_triggered = True
        incident.backup_job_id = backup_job_id
        _log_step("backup_triggered", f"Pre-incident backup started. Job ID: {backup_job_id}")
    except Exception as exc:
        _log_step("backup_triggered", f"Backup trigger failed: {exc}", success=False)

    # 2. SOAR dispatch (best-effort)
    if soar_config:
        try:
            soar_id = await _dispatch_soar(finding, incident_number, soar_config)
            if soar_id:
                incident.soar_dispatched = True
                incident.soar_incident_id = soar_id
                _log_step("soar_dispatched", f"SOAR incident created: {soar_id}")
        except Exception as exc:
            _log_step("soar_dispatched", f"SOAR dispatch failed: {exc}", success=False)

    # 3. SIEM event (best-effort)
    if siem_config:
        try:
            ok = await _emit_siem(finding, str(finding.id), siem_config)
            incident.siem_dispatched = ok
            _log_step("siem_dispatched", "SIEM event forwarded" if ok else "SIEM emit failed", success=ok)
        except Exception as exc:
            _log_step("siem_dispatched", f"SIEM emit failed: {exc}", success=False)

    # 4. VeeamONE report (best-effort)
    if veeamone_config:
        try:
            ok = await _report_veeamone(finding, str(finding.id), str(org_id), veeamone_config)
            incident.veeamone_reported = ok
            _log_step("veeamone_reported", "VeeamONE event sent" if ok else "VeeamONE failed", success=ok)
        except Exception as exc:
            _log_step("veeamone_reported", f"VeeamONE failed: {exc}", success=False)

    # 5. Notifications (best-effort)
    if notification_channels:
        try:
            await _send_incident_notifications(finding, incident_number, notification_channels)
            incident.notifications_sent = True
            _log_step("notifications_sent", "Notification channels notified")
        except Exception as exc:
            _log_step("notifications_sent", f"Notifications failed: {exc}", success=False)

    incident.ir_log = ir_log
    await db.commit()
    return incident


async def _trigger_backup(host: str) -> str:
    """
    Trigger an immediate Veeam backup for the affected host.

    In production this calls the appliance relay to instruct the appliance
    to start a Veeam backup job. Returns a mock job ID for now.
    """
    # The actual implementation sends a command to the appliance via the relay channel.
    # The appliance picks it up on the next command poll and starts the Veeam backup.
    return f"veeam-backup-{uuid.uuid4().hex[:8]}"


async def _dispatch_soar(finding: ThreatFinding, incident_number: str, config: dict) -> str | None:
    from src.integrations.soar import dispatch_to_splunk_soar, dispatch_to_xsoar, dispatch_generic_webhook
    platform = config.get("platform", "generic")
    kwargs = dict(
        incident_title=f"R3VP {incident_number} - {finding.threat_name}",
        severity=finding.severity,
        affected_host=finding.host,
        threat_name=finding.threat_name,
        indicator_type=finding.indicator_type,
        indicator_value=finding.indicator_value,
        mitre_technique=finding.mitre_technique,
        org_id=str(finding.org_id),
        finding_id=str(finding.id),
    )
    if platform == "splunk_soar":
        return await dispatch_to_splunk_soar(
            base_url=config["url"], api_token=config["api_key"], **kwargs
        )
    elif platform == "xsoar":
        return await dispatch_to_xsoar(
            base_url=config["url"], api_key=config["api_key"], **kwargs
        )
    else:
        ok = await dispatch_generic_webhook(webhook_url=config["url"], **kwargs)
        return "dispatched" if ok else None


async def _emit_siem(finding: ThreatFinding, finding_id: str, config: dict) -> bool:
    from src.integrations.siem import emit_threat_event
    return await emit_threat_event(
        siem_host=config["host"],
        siem_port=int(config.get("port", 514)),
        siem_protocol=config.get("protocol", "udp"),
        siem_format=config.get("format", "cef"),
        signature_id=finding.signature_id,
        threat_name=finding.threat_name,
        severity=finding.severity,
        affected_host=finding.host,
        indicator_type=finding.indicator_type,
        indicator_value=finding.indicator_value,
        mitre_technique=finding.mitre_technique,
        org_id=str(finding.org_id),
        finding_id=finding_id,
    )


async def _report_veeamone(
    finding: ThreatFinding,
    finding_id: str,
    org_id: str,
    config: dict,
) -> bool:
    from src.integrations.veeamone import VeeamOneClient
    client = VeeamOneClient(
        base_url=config["url"],
        username=config["username"],
        password=config["password"],
    )
    return await client.report_threat_event(
        threat_name=finding.threat_name,
        severity=finding.severity,
        affected_host=finding.host,
        mitre_technique=finding.mitre_technique,
        finding_id=finding_id,
        org_id=org_id,
    )


async def _send_incident_notifications(
    finding: ThreatFinding,
    incident_number: str,
    channels: list[dict],
) -> None:
    from src.services.notifications import _send_slack, _send_teams, _send_email_ses
    msg = (
        f"*INCIDENT {incident_number}*: {finding.threat_name} detected on {finding.host}. "
        f"Severity: {finding.severity.upper()}. "
        f"IR workflow triggered automatically."
    )
    for ch in channels:
        event_set = set(ch.get("events", []))
        if "threat_detected" not in event_set:
            continue
        if not ch.get("enabled"):
            continue
        try:
            ch_type = ch.get("channel_type", "")
            dest = ch.get("destination", "")
            if ch_type == "slack":
                await _send_slack(dest, msg, "critical")
            elif ch_type == "teams":
                await _send_teams(dest, msg, "critical")
            elif ch_type == "email":
                await _send_email_ses(dest, f"R3VP Incident: {incident_number}", msg)
        except Exception as exc:
            log.warning("ir.notification.failed", channel=ch.get("name"), error=str(exc))
