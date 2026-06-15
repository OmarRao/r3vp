"""
YARA rules engine for the R3VP appliance.

Loads YARA rules from the threat database and applies them to files
in configured scan paths.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy -- https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import structlog

from .models import ScanFinding, ThreatSeverity, ThreatType

log = structlog.get_logger()

# Built-in YARA rules for common threat patterns
BUILTIN_YARA_RULES = """
rule win_dropper_generic_v3 {
    meta:
        description = "Generic Windows dropper pattern"
        severity = "medium"
        mitre_technique = "T1105"
    strings:
        $a = "URLDownloadToFile" ascii
        $b = "ShellExecuteEx" ascii
        $c = { 4D 5A 90 00 }  // MZ header
    condition:
        $c at 0 and $a and $b
}

rule ransomware_file_marker {
    meta:
        description = "Generic ransomware file encryption marker"
        severity = "critical"
        mitre_technique = "T1486"
    strings:
        $readme1 = "YOUR FILES HAVE BEEN ENCRYPTED" nocase
        $readme2 = "To decrypt your files" nocase
        $readme3 = "BTC" nocase
        $readme4 = ".onion" nocase
    condition:
        2 of ($readme*)
}

rule credential_dump_strings {
    meta:
        description = "Credential dumping tool strings"
        severity = "high"
        mitre_technique = "T1003"
    strings:
        $a = "sekurlsa" ascii nocase
        $b = "lsadump" ascii nocase
        $c = "wdigest" ascii nocase
        $d = "kerberos" ascii nocase
    condition:
        2 of them
}
"""


class YaraEngine:
    """
    Compiles and applies YARA rules from the threat database.

    Falls back gracefully if yara-python is not installed or rules fail
    to compile, so the scanner still works without YARA support.
    """

    def __init__(self) -> None:
        self._rules = None
        self._rule_count = 0
        self._available = self._check_yara()

    def _check_yara(self) -> bool:
        try:
            import yara  # noqa: F401
            return True
        except ImportError:
            log.warning("yara_engine.yara_not_installed")
            return False

    def load_rules(self, db_rules: list[dict]) -> None:
        """Compile YARA rules from the database plus built-in rules."""
        if not self._available:
            return
        import yara

        # Write rules to a temp file for compilation
        combined = BUILTIN_YARA_RULES + "\n"
        for rule in db_rules:
            combined += f"\n{rule['rule_text']}\n"

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yar", delete=False
            ) as f:
                f.write(combined)
                tmp_path = f.name

            self._rules = yara.compile(filepath=tmp_path)
            # Count rules by scanning an empty string
            self._rule_count = len(db_rules) + 3  # 3 built-in rules
            log.info("yara_engine.rules_loaded", count=self._rule_count)
        except yara.SyntaxError as exc:
            log.error("yara_engine.compile_failed", error=str(exc))
            self._rules = None

    def scan_paths(
        self, paths: list[Path], hostname: str
    ) -> tuple[list[ScanFinding], int]:
        """Scan files at the given paths with loaded YARA rules."""
        if not self._available or not self._rules:
            return [], 0

        findings: list[ScanFinding] = []
        for path in paths:
            try:
                for filepath in Path(path).rglob("*"):
                    if not filepath.is_file():
                        continue
                    try:
                        matches = self._rules.match(str(filepath))
                        for match in matches:
                            severity_str = match.meta.get("severity", "medium")
                            severity = ThreatSeverity(severity_str)
                            mitre = match.meta.get("mitre_technique")
                            findings.append(
                                ScanFinding(
                                    signature_id=f"yara-{match.rule}",
                                    threat_name=match.rule,
                                    threat_type=ThreatType.YARA,
                                    severity=severity,
                                    host=hostname,
                                    indicator_type="yara",
                                    indicator_value=match.rule,
                                    context={
                                        "file": str(filepath),
                                        "strings": [str(s) for s in match.strings[:5]],
                                    },
                                    mitre_technique=mitre,
                                )
                            )
                    except Exception:
                        pass
            except Exception as exc:
                log.warning("yara_scan.path_error", path=str(path), error=str(exc))

        return findings, self._rule_count
