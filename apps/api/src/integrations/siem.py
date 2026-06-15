"""
SIEM integration for R3VP.

Emits structured security events in CEF (Common Event Format),
LEEF (IBM QRadar), and JSON-over-Syslog formats for Splunk, QRadar,
and Microsoft Sentinel.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy -- https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import asyncio
import json
import socket
from datetime import datetime, timezone

import structlog

log = structlog.get_logger()

# CEF header: CEF:Version|Device Vendor|Device Product|Device Version|SignatureID|Name|Severity|Extension
_CEF_VERSION = "CEF:0"
_VENDOR = "R3VP"
_PRODUCT = "RecoveryValidation"
_VERSION = "0.4.0"

_SEVERITY_CEF = {"critical": "10", "high": "8", "medium": "5", "low": "2", "info": "1"}
_SEVERITY_LEEF = {"critical": "10", "high": "8", "medium": "5", "low": "2", "info": "1"}


def build_cef_event(
    *,
    signature_id: str,
    threat_name: str,
    severity: str,
    affected_host: str,
    indicator_type: str,
    indicator_value: str,
    mitre_technique: str | None,
    org_id: str,
    finding_id: str,
) -> str:
    """Build a CEF-formatted event string."""
    cef_sev = _SEVERITY_CEF.get(severity, "5")
    ts = datetime.now(timezone.utc).strftime("%b %d %Y %H:%M:%S")
    extension = (
        f"rt={ts} "
        f"dhost={affected_host} "
        f"cs1={indicator_type} "
        f"cs1Label=IndicatorType "
        f"cs2={indicator_value} "
        f"cs2Label=IndicatorValue "
        f"cs3={mitre_technique or ''} "
        f"cs3Label=MITRETechnique "
        f"cs4={org_id} "
        f"cs4Label=OrgID "
        f"cs5={finding_id} "
        f"cs5Label=FindingID"
    )
    return (
        f"{_CEF_VERSION}|{_VENDOR}|{_PRODUCT}|{_VERSION}"
        f"|{signature_id}|{threat_name}|{cef_sev}|{extension}"
    )


def build_leef_event(
    *,
    signature_id: str,
    threat_name: str,
    severity: str,
    affected_host: str,
    indicator_type: str,
    indicator_value: str,
    mitre_technique: str | None,
    org_id: str,
    finding_id: str,
) -> str:
    """Build a LEEF-formatted event string for IBM QRadar."""
    leef_sev = _SEVERITY_LEEF.get(severity, "5")
    ts = datetime.now(timezone.utc).isoformat()
    return (
        f"LEEF:2.0|{_VENDOR}|{_PRODUCT}|{_VERSION}|{signature_id}|"
        f"devTime={ts}\t"
        f"sev={leef_sev}\t"
        f"dst={affected_host}\t"
        f"indicatorType={indicator_type}\t"
        f"indicatorValue={indicator_value}\t"
        f"mitreId={mitre_technique or ''}\t"
        f"orgId={org_id}\t"
        f"findingId={finding_id}"
    )


async def send_syslog(
    host: str,
    port: int,
    message: str,
    protocol: str = "udp",
) -> bool:
    """Send a syslog message over UDP or TCP."""
    try:
        # RFC 5424 syslog header: <priority>version timestamp hostname appname procid msgid
        priority = 134  # facility=local0 (16), severity=info (6) -> (16*8)+6=134
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        syslog_msg = f"<{priority}>1 {ts} r3vp-appliance R3VP - - - {message}\n"
        data = syslog_msg.encode("utf-8")

        if protocol.lower() == "tcp":
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(data)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        else:
            loop = asyncio.get_event_loop()
            transport, _ = await loop.create_datagram_endpoint(
                asyncio.DatagramProtocol,
                remote_addr=(host, port),
            )
            transport.sendto(data)
            transport.close()
        log.info("siem.syslog.sent", host=host, port=port)
        return True
    except Exception as exc:
        log.error("siem.syslog.failed", host=host, port=port, error=str(exc))
        return False


async def emit_threat_event(
    *,
    siem_host: str,
    siem_port: int,
    siem_protocol: str,
    siem_format: str,  # "cef", "leef", "json"
    signature_id: str,
    threat_name: str,
    severity: str,
    affected_host: str,
    indicator_type: str,
    indicator_value: str,
    mitre_technique: str | None,
    org_id: str,
    finding_id: str,
) -> bool:
    """Build and emit a threat event to the configured SIEM."""
    if siem_format.lower() == "cef":
        msg = build_cef_event(
            signature_id=signature_id, threat_name=threat_name, severity=severity,
            affected_host=affected_host, indicator_type=indicator_type,
            indicator_value=indicator_value, mitre_technique=mitre_technique,
            org_id=org_id, finding_id=finding_id,
        )
    elif siem_format.lower() == "leef":
        msg = build_leef_event(
            signature_id=signature_id, threat_name=threat_name, severity=severity,
            affected_host=affected_host, indicator_type=indicator_type,
            indicator_value=indicator_value, mitre_technique=mitre_technique,
            org_id=org_id, finding_id=finding_id,
        )
    else:
        # JSON syslog
        msg = json.dumps({
            "source": "r3vp", "event": "threat_detected",
            "threat_name": threat_name, "severity": severity,
            "affected_host": affected_host, "indicator_type": indicator_type,
            "indicator_value": indicator_value, "mitre_technique": mitre_technique,
            "org_id": org_id, "finding_id": finding_id,
        })

    return await send_syslog(siem_host, siem_port, msg, siem_protocol)
