"""
Threat signature database for the R3VP appliance.

Maintains a local SQLite database of threat signatures, synced from the
R3VP cloud feed. Provides fast lookup methods for the scanner.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy -- https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import structlog

from .models import ThreatSignature, ThreatSeverity, ThreatType

if TYPE_CHECKING:
    pass

log = structlog.get_logger()

# Built-in seed signatures covering the most common ransomware families.
# The cloud sync endpoint supplements these with the latest threat intelligence.
SEED_SIGNATURES: list[dict] = [
    {
        "id": "ransomware-lockbit3",
        "name": "LockBit 3.0",
        "family": "LockBit",
        "threat_type": "ransomware",
        "severity": "critical",
        "process_names": ["svchost32.exe", "lockbit.exe", "lb3.exe"],
        "file_hashes": [],
        "file_paths": ["*\\AppData\\Roaming\\*.exe", "*\\Temp\\LB3*"],
        "registry_keys": [
            "HKCU\\Software\\BlockInput",
            "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options\\",
        ],
        "network_iocs": ["185.220.101.47", "lockbit3ouyhpne.onion"],
        "mitre_technique": "T1486",
        "description": "LockBit 3.0 ransomware - encrypts files and demands ransom.",
        "remediation": "Isolate host immediately. Restore from pre-incident backup.",
    },
    {
        "id": "ransomware-blackcat",
        "name": "BlackCat/ALPHV",
        "family": "BlackCat",
        "threat_type": "ransomware",
        "severity": "critical",
        "process_names": ["alphv.exe", "blackcat.exe"],
        "file_hashes": [],
        "file_paths": ["*\\Temp\\alphv*"],
        "registry_keys": [],
        "network_iocs": ["185.220.101.48", "alphvmmm27oispztk.onion"],
        "mitre_technique": "T1486",
        "description": "BlackCat (ALPHV) ransomware written in Rust.",
        "remediation": "Isolate host immediately. Restore from pre-incident backup.",
    },
    {
        "id": "ransomware-clop",
        "name": "Cl0p Ransomware",
        "family": "Cl0p",
        "threat_type": "ransomware",
        "severity": "critical",
        "process_names": ["clop.exe", "clopReadMe.exe"],
        "file_hashes": [],
        "file_paths": ["*.clop", "*.Clop"],
        "registry_keys": [],
        "network_iocs": [],
        "mitre_technique": "T1486",
        "description": "Cl0p ransomware, frequently used in MOVEit and GoAnywhere attacks.",
        "remediation": "Isolate host. Check for exfiltration. Restore from backup.",
    },
    {
        "id": "apt-apt29-persistence",
        "name": "APT29 Registry Persistence",
        "family": "APT29 (Cozy Bear)",
        "threat_type": "apt",
        "severity": "high",
        "process_names": [],
        "file_hashes": [],
        "file_paths": [],
        "registry_keys": [
            "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\",
            "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\",
        ],
        "network_iocs": [],
        "mitre_technique": "T1547.001",
        "description": "APT29 persistence technique via registry run keys.",
        "remediation": "Review and remove unauthorised run keys. Investigate lateral movement.",
    },
    {
        "id": "cve-2024-40711",
        "name": "CVE-2024-40711 - Veeam B&R RCE",
        "family": "Veeam Vulnerability",
        "threat_type": "cve",
        "severity": "critical",
        "process_names": ["Veeam.Backup.Service.exe"],
        "file_hashes": [],
        "file_paths": [],
        "registry_keys": [],
        "network_iocs": [],
        "mitre_technique": "T1190",
        "cve_id": "CVE-2024-40711",
        "cvss_score": 9.8,
        "description": "Critical RCE vulnerability in Veeam Backup & Replication 12.1 and earlier.",
        "remediation": "Upgrade to Veeam B&R 12.1.2.172 or later immediately.",
    },
    {
        "id": "malware-mimikatz",
        "name": "Mimikatz Credential Dumper",
        "family": "Mimikatz",
        "threat_type": "malware",
        "severity": "high",
        "process_names": ["mimikatz.exe", "mimilib.dll"],
        "file_hashes": [
            "fc525c9683e8fe067095ba2ddc971889dc76cec2",
        ],
        "file_paths": ["*\\mimikatz*", "*\\sekurlsa*"],
        "registry_keys": [],
        "network_iocs": [],
        "mitre_technique": "T1003",
        "description": "Credential dumping tool used by many threat actors.",
        "remediation": "Remove file. Rotate all credentials. Investigate how it arrived.",
    },
]


class ThreatDatabase:
    """
    Local SQLite threat signature database.

    Call `initialise()` once at startup to create the schema and seed signatures.
    Call `sync_from_cloud()` periodically to refresh from the cloud feed.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def initialise(self) -> None:
        """Create schema and seed built-in signatures."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_schema()
        self._seed_signatures()
        log.info("threat_database.initialised", path=str(self._db_path))

    def _create_schema(self) -> None:
        assert self._conn
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS signatures (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                family TEXT NOT NULL,
                threat_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                process_names TEXT NOT NULL DEFAULT '[]',
                file_hashes TEXT NOT NULL DEFAULT '[]',
                file_paths TEXT NOT NULL DEFAULT '[]',
                registry_keys TEXT NOT NULL DEFAULT '[]',
                network_iocs TEXT NOT NULL DEFAULT '[]',
                mitre_technique TEXT,
                cve_id TEXT,
                cvss_score REAL,
                description TEXT NOT NULL DEFAULT '',
                remediation TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS yara_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source TEXT NOT NULL,
                rule_text TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                synced_at TEXT NOT NULL,
                signatures_added INTEGER NOT NULL DEFAULT 0,
                signatures_updated INTEGER NOT NULL DEFAULT 0,
                error TEXT
            );
            """
        )
        self._conn.commit()

    def _seed_signatures(self) -> None:
        assert self._conn
        now = datetime.now(timezone.utc).isoformat()
        for sig in SEED_SIGNATURES:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO signatures
                    (id, name, family, threat_type, severity, process_names, file_hashes,
                     file_paths, registry_keys, network_iocs, mitre_technique, cve_id,
                     cvss_score, description, remediation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sig["id"], sig["name"], sig["family"],
                    sig["threat_type"], sig["severity"],
                    json.dumps(sig.get("process_names", [])),
                    json.dumps(sig.get("file_hashes", [])),
                    json.dumps(sig.get("file_paths", [])),
                    json.dumps(sig.get("registry_keys", [])),
                    json.dumps(sig.get("network_iocs", [])),
                    sig.get("mitre_technique"),
                    sig.get("cve_id"),
                    sig.get("cvss_score"),
                    sig.get("description", ""),
                    sig.get("remediation", ""),
                    now,
                ),
            )
        self._conn.commit()

    def get_all_signatures(self) -> list[ThreatSignature]:
        """Return all signatures from the database."""
        assert self._conn
        rows = self._conn.execute("SELECT * FROM signatures").fetchall()
        return [self._row_to_signature(r) for r in rows]

    def get_process_signatures(self) -> list[ThreatSignature]:
        """Return only signatures that have process name indicators."""
        assert self._conn
        rows = self._conn.execute(
            "SELECT * FROM signatures WHERE process_names != '[]'"
        ).fetchall()
        return [self._row_to_signature(r) for r in rows]

    def get_hash_signatures(self) -> list[ThreatSignature]:
        """Return only signatures that have file hash indicators."""
        assert self._conn
        rows = self._conn.execute(
            "SELECT * FROM signatures WHERE file_hashes != '[]'"
        ).fetchall()
        return [self._row_to_signature(r) for r in rows]

    def get_network_signatures(self) -> list[ThreatSignature]:
        """Return signatures with network IOC indicators."""
        assert self._conn
        rows = self._conn.execute(
            "SELECT * FROM signatures WHERE network_iocs != '[]'"
        ).fetchall()
        return [self._row_to_signature(r) for r in rows]

    def signature_count(self) -> int:
        assert self._conn
        return self._conn.execute("SELECT COUNT(*) FROM signatures").fetchone()[0]

    def get_yara_rules(self) -> list[dict]:
        """Return all enabled YARA rules."""
        assert self._conn
        rows = self._conn.execute(
            "SELECT id, name, rule_text FROM yara_rules WHERE enabled = 1"
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_yara_rule(self, rule_id: str, name: str, source: str, rule_text: str) -> None:
        assert self._conn
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO yara_rules (id, name, source, rule_text, enabled, updated_at)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                rule_text = excluded.rule_text,
                updated_at = excluded.updated_at
            """,
            (rule_id, name, source, rule_text, now),
        )
        self._conn.commit()

    async def sync_from_cloud(self, feed_url: str, api_key: str) -> dict:
        """Fetch latest signatures from the R3VP cloud threat feed."""
        added = 0
        updated = 0
        error = None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    feed_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                signatures = data.get("signatures", [])
                now = datetime.now(timezone.utc).isoformat()
                assert self._conn
                for sig in signatures:
                    existing = self._conn.execute(
                        "SELECT id FROM signatures WHERE id = ?", (sig["id"],)
                    ).fetchone()
                    self._conn.execute(
                        """
                        INSERT INTO signatures
                            (id, name, family, threat_type, severity, process_names,
                             file_hashes, file_paths, registry_keys, network_iocs,
                             mitre_technique, cve_id, cvss_score, description, remediation, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            name = excluded.name,
                            severity = excluded.severity,
                            process_names = excluded.process_names,
                            file_hashes = excluded.file_hashes,
                            network_iocs = excluded.network_iocs,
                            updated_at = excluded.updated_at
                        """,
                        (
                            sig["id"], sig["name"], sig.get("family", ""),
                            sig.get("threat_type", "malware"), sig.get("severity", "medium"),
                            json.dumps(sig.get("process_names", [])),
                            json.dumps(sig.get("file_hashes", [])),
                            json.dumps(sig.get("file_paths", [])),
                            json.dumps(sig.get("registry_keys", [])),
                            json.dumps(sig.get("network_iocs", [])),
                            sig.get("mitre_technique"),
                            sig.get("cve_id"),
                            sig.get("cvss_score"),
                            sig.get("description", ""),
                            sig.get("remediation", ""),
                            now,
                        ),
                    )
                    if existing:
                        updated += 1
                    else:
                        added += 1
                self._conn.commit()
        except Exception as exc:
            error = str(exc)
            log.warning("threat_database.sync_failed", error=error)
        finally:
            assert self._conn
            self._conn.execute(
                "INSERT INTO sync_log (synced_at, signatures_added, signatures_updated, error) VALUES (?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), added, updated, error),
            )
            self._conn.commit()
        return {"added": added, "updated": updated, "error": error}

    @staticmethod
    def _row_to_signature(row: sqlite3.Row) -> ThreatSignature:
        return ThreatSignature(
            id=row["id"],
            name=row["name"],
            family=row["family"],
            threat_type=ThreatType(row["threat_type"]),
            severity=ThreatSeverity(row["severity"]),
            process_names=json.loads(row["process_names"]),
            file_hashes=json.loads(row["file_hashes"]),
            file_paths=json.loads(row["file_paths"]),
            registry_keys=json.loads(row["registry_keys"]),
            network_iocs=json.loads(row["network_iocs"]),
            mitre_technique=row["mitre_technique"],
            cve_id=row["cve_id"],
            cvss_score=row["cvss_score"],
            description=row["description"],
            remediation=row["remediation"],
        )
