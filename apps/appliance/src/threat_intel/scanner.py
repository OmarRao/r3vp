"""
Threat scanner for the R3VP appliance.

Scans running processes, network connections, and configured file paths
against the threat signature database and YARA rules.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy -- https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import hashlib
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psutil
import structlog

from .database import ThreatDatabase
from .models import ScanFinding, ScanResult, ThreatSeverity, ThreatType
from .yara_engine import YaraEngine

log = structlog.get_logger()


class ThreatScanner:
    """
    Scans the local environment for indicators of compromise.

    Checks:
    - Running process names against signature database
    - Active network connections against known malicious IPs
    - File hashes in scan paths against signature database
    - YARA rules against files in scan paths
    """

    def __init__(
        self,
        db: ThreatDatabase,
        yara_engine: YaraEngine,
        scan_paths: list[Path] | None = None,
    ) -> None:
        self._db = db
        self._yara = yara_engine
        self._scan_paths = scan_paths or []

    async def run_full_scan(
        self,
        appliance_id: str,
        org_id: str,
    ) -> ScanResult:
        """Run a complete threat scan and return findings."""
        scan_id = str(uuid.uuid4())
        started = datetime.now(timezone.utc)
        findings: list[ScanFinding] = []
        hostname = socket.gethostname()

        log.info("threat_scan.started", scan_id=scan_id)

        # Load signatures once
        proc_sigs = self._db.get_process_signatures()
        hash_sigs = self._db.get_hash_signatures()
        net_sigs = self._db.get_network_signatures()
        all_sigs = self._db.get_all_signatures()
        sig_count = self._db.signature_count()

        # 1. Process scan
        proc_findings = self._scan_processes(proc_sigs, hostname)
        findings.extend(proc_findings)

        # 2. Network connection scan
        net_findings = self._scan_network_connections(net_sigs, hostname)
        findings.extend(net_findings)

        # 3. File system scan (if paths configured)
        file_findings = []
        yara_count = 0
        if self._scan_paths:
            file_findings = self._scan_files(hash_sigs, hostname)
            findings.extend(file_findings)
            # YARA scan
            yara_findings, yara_count = self._yara.scan_paths(self._scan_paths, hostname)
            findings.extend(yara_findings)

        completed = datetime.now(timezone.utc)
        result = ScanResult(
            scan_id=scan_id,
            appliance_id=appliance_id,
            org_id=org_id,
            started_at=started,
            completed_at=completed,
            hosts_scanned=1,
            findings=findings,
            signatures_checked=sig_count,
            yara_rules_checked=yara_count,
        )

        log.info(
            "threat_scan.completed",
            scan_id=scan_id,
            findings=len(findings),
            critical=result.critical_count,
            high=result.high_count,
            duration_secs=(completed - started).total_seconds(),
        )
        return result

    def _scan_processes(self, sigs, hostname: str) -> list[ScanFinding]:
        """Cross-reference running processes against signature process name IOCs."""
        findings: list[ScanFinding] = []
        try:
            running = {p.name().lower(): p for p in psutil.process_iter(["pid", "name", "exe"])}
        except Exception as exc:
            log.warning("process_scan.error", error=str(exc))
            return findings

        for sig in sigs:
            for proc_name in sig.process_names:
                match_name = proc_name.lower()
                if match_name in running:
                    proc = running[match_name]
                    try:
                        pid = proc.pid
                        exe = proc.exe() if hasattr(proc, "exe") else ""
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pid = 0
                        exe = ""
                    findings.append(
                        ScanFinding(
                            signature_id=sig.id,
                            threat_name=sig.name,
                            threat_type=sig.threat_type,
                            severity=sig.severity,
                            host=hostname,
                            indicator_type="process",
                            indicator_value=proc_name,
                            context={"pid": pid, "exe": exe},
                            mitre_technique=sig.mitre_technique,
                        )
                    )
                    log.warning(
                        "threat_scan.process_match",
                        threat=sig.name,
                        process=proc_name,
                        pid=pid,
                    )
        return findings

    def _scan_network_connections(self, sigs, hostname: str) -> list[ScanFinding]:
        """Check active network connections against known malicious IPs."""
        findings: list[ScanFinding] = []
        try:
            connections = psutil.net_connections(kind="inet")
        except Exception as exc:
            log.warning("network_scan.error", error=str(exc))
            return findings

        remote_ips = {c.raddr.ip for c in connections if c.raddr}

        for sig in sigs:
            for ioc in sig.network_iocs:
                # Only match plain IP addresses here (not .onion addresses)
                if ioc in remote_ips:
                    findings.append(
                        ScanFinding(
                            signature_id=sig.id,
                            threat_name=sig.name,
                            threat_type=sig.threat_type,
                            severity=sig.severity,
                            host=hostname,
                            indicator_type="network",
                            indicator_value=ioc,
                            context={"remote_ip": ioc},
                            mitre_technique=sig.mitre_technique,
                        )
                    )
                    log.warning("threat_scan.network_match", threat=sig.name, ioc=ioc)
        return findings

    def _scan_files(self, sigs, hostname: str) -> list[ScanFinding]:
        """Hash files in scan paths and compare against signature file hash IOCs."""
        findings: list[ScanFinding] = []
        # Build a set of all known bad hashes for fast lookup
        hash_to_sig: dict[str, object] = {}
        for sig in sigs:
            for h in sig.file_hashes:
                hash_to_sig[h.lower()] = sig

        if not hash_to_sig:
            return findings

        for scan_path in self._scan_paths:
            try:
                for filepath in Path(scan_path).rglob("*"):
                    if not filepath.is_file():
                        continue
                    try:
                        file_hash = _sha256(filepath)
                        if file_hash in hash_to_sig:
                            sig = hash_to_sig[file_hash]
                            findings.append(
                                ScanFinding(
                                    signature_id=sig.id,  # type: ignore[attr-defined]
                                    threat_name=sig.name,  # type: ignore[attr-defined]
                                    threat_type=sig.threat_type,  # type: ignore[attr-defined]
                                    severity=sig.severity,  # type: ignore[attr-defined]
                                    host=hostname,
                                    indicator_type="file_hash",
                                    indicator_value=file_hash,
                                    context={"path": str(filepath)},
                                    mitre_technique=sig.mitre_technique,  # type: ignore[attr-defined]
                                )
                            )
                    except (PermissionError, OSError):
                        pass
            except Exception as exc:
                log.warning("file_scan.error", path=str(scan_path), error=str(exc))
        return findings


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
