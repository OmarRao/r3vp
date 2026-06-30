"""Threat intelligence data models for the appliance scanner."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ThreatSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatType(str, Enum):
    RANSOMWARE = "ransomware"
    MALWARE = "malware"
    APT = "apt"
    CVE = "cve"
    YARA = "yara"


@dataclass
class ThreatSignature:
    """A single threat signature from the database."""
    id: str
    name: str
    family: str
    threat_type: ThreatType
    severity: ThreatSeverity
    # Indicators of compromise
    process_names: list[str] = field(default_factory=list)
    file_hashes: list[str] = field(default_factory=list)        # SHA-256 hex strings
    file_paths: list[str] = field(default_factory=list)         # glob patterns
    registry_keys: list[str] = field(default_factory=list)
    network_iocs: list[str] = field(default_factory=list)       # IP addresses or domains
    # Metadata
    mitre_technique: str | None = None
    cve_id: str | None = None
    cvss_score: float | None = None
    description: str = ""
    remediation: str = ""
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScanFinding:
    """A single finding from a threat scan."""
    signature_id: str
    threat_name: str
    threat_type: ThreatType
    severity: ThreatSeverity
    host: str
    indicator_type: str   # "process", "file_hash", "network", "registry", "yara"
    indicator_value: str  # the matched value
    context: dict = field(default_factory=dict)
    mitre_technique: str | None = None
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScanResult:
    """The result of a complete threat scan."""
    scan_id: str
    appliance_id: str
    org_id: str
    started_at: datetime
    completed_at: datetime
    hosts_scanned: int
    findings: list[ScanFinding] = field(default_factory=list)
    signatures_checked: int = 0
    yara_rules_checked: int = 0
    error: str | None = None

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ThreatSeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ThreatSeverity.HIGH)

    @property
    def has_critical_threat(self) -> bool:
        return self.critical_count > 0
