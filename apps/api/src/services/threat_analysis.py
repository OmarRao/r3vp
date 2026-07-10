"""Ransomware-indicator analysis over backup restore-point metadata.

Given lightweight metadata the appliance can derive per restore point (average
file entropy, file counts, rename counts, newly-seen extensions), this flags
likely ransomware activity *before* a restore and recommends the newest clean
restore point. Pure and side-effect free so it is fully unit-testable.

Detected indicators map to MITRE ATT&CK T1486 (Data Encrypted for Impact).

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
from __future__ import annotations

from typing import Any

# File extensions strongly associated with known ransomware families.
KNOWN_RANSOMWARE_EXTENSIONS: frozenset[str] = frozenset({
    "locky", "wcry", "wncry", "wncryt", "crypto", "crypt", "encrypted", "enc",
    "cerber", "zepto", "odin", "aesir", "locked", "ryuk", "conti", "lockbit",
    "ryk", "makop", "phobos", "djvu", "stop", "revil", "sodinokibi", "maze",
    "egregor", "clop", "darkside", "blackcat", "royal", "akira", "cactus",
})

# Shannon entropy is bounded at 8.0 bits/byte; values near the ceiling indicate
# compressed or encrypted content across the file set.
ENTROPY_CEILING = 8.0
ENTROPY_ENCRYPTED_THRESHOLD = 7.9
# A single-interval jump in average entropy this large is suspicious even below
# the absolute threshold.
ENTROPY_SPIKE_DELTA = 1.5
# Fraction of files renamed within one restore-point interval that looks like a
# mass-encryption rename sweep.
MASS_RENAME_RATIO = 0.25

_SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def match_ransomware_extensions(extensions: list[str]) -> list[str]:
    """Return the subset of ``extensions`` that match known ransomware families."""
    hits = []
    for ext in extensions:
        norm = ext.lower().lstrip(".")
        if norm in KNOWN_RANSOMWARE_EXTENSIONS:
            hits.append(norm)
    return sorted(set(hits))


def _indicators_for(rp: dict[str, Any], entropy_baseline: float | None) -> list[dict[str, Any]]:
    indicators: list[dict[str, Any]] = []

    entropy = float(rp.get("avg_entropy", 0) or 0)
    if entropy >= ENTROPY_ENCRYPTED_THRESHOLD:
        indicators.append({
            "type": "entropy_anomaly",
            "severity": "high",
            "mitre_technique": "T1486",
            "detail": f"Average file entropy {entropy:.2f} of {ENTROPY_CEILING} suggests mass encryption",
        })
    elif entropy_baseline is not None and entropy - entropy_baseline >= ENTROPY_SPIKE_DELTA:
        indicators.append({
            "type": "entropy_spike",
            "severity": "medium",
            "mitre_technique": "T1486",
            "detail": f"Entropy jumped {entropy - entropy_baseline:.2f} vs prior restore points",
        })

    total = int(rp.get("total_files", 0) or 0)
    renamed = int(rp.get("renamed_files", 0) or 0)
    if total and renamed / total >= MASS_RENAME_RATIO:
        indicators.append({
            "type": "mass_file_rename",
            "severity": "high",
            "mitre_technique": "T1486",
            "detail": f"{renamed} of {total} files renamed ({round(renamed / total * 100)}%)",
        })

    ext_hits = match_ransomware_extensions(list(rp.get("new_extensions", []) or []))
    if ext_hits:
        indicators.append({
            "type": "ransomware_extension",
            "severity": "critical",
            "mitre_technique": "T1486",
            "detail": f"Known ransomware extensions present: {', '.join(ext_hits)}",
        })

    return indicators


def analyze_restore_points(restore_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Analyze restore points (oldest first) and return per-point results.

    Each result has the restore point id, its indicators, the highest severity,
    and whether it is clean (no high or critical indicator).
    """
    results: list[dict[str, Any]] = []
    seen_entropies: list[float] = []
    for rp in restore_points:
        baseline = (
            sorted(seen_entropies)[len(seen_entropies) // 2] if seen_entropies else None
        )
        indicators = _indicators_for(rp, baseline)
        max_sev = "none"
        for ind in indicators:
            if _SEVERITY_ORDER[ind["severity"]] > _SEVERITY_ORDER[max_sev]:
                max_sev = ind["severity"]
        results.append({
            "restore_point_id": rp.get("id"),
            "created_at": rp.get("created_at"),
            "indicators": indicators,
            "max_severity": max_sev,
            "is_clean": _SEVERITY_ORDER[max_sev] < _SEVERITY_ORDER["high"],
        })
        seen_entropies.append(float(rp.get("avg_entropy", 0) or 0))
    return results


def select_clean_restore_point(restore_points: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest clean restore point (by created_at), or None if all are
    flagged. Restore points without a created_at fall back to input order."""
    analyzed = analyze_restore_points(restore_points)
    clean = [a for a in analyzed if a["is_clean"]]
    if not clean:
        return None
    return max(clean, key=lambda a: (a["created_at"] is not None, a["created_at"] or ""))
