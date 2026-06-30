"""False-positive suppression for threat-intel scan results."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Allowed base directory for false-positive definition files
_FP_BASE_DIR = Path(os.environ.get("R3VP_FP_DIR", "/var/r3vp/false_positives")).resolve()


def _safe_fp_path(relative_path: str) -> Path:
    """Resolve *relative_path* and verify it stays within the allowed base dir.

    Raises ValueError on path-traversal attempts (CWE-22).
    """
    resolved = (_FP_BASE_DIR / relative_path).resolve()
    if not str(resolved).startswith(str(_FP_BASE_DIR)):
        raise ValueError(
            f"Path traversal detected: {relative_path!r} resolves outside false-positives directory"
        )
    return resolved


def load_false_positive_list(list_name: str) -> list[dict[str, Any]]:
    """Load a false-positive definition list by name.

    *list_name* is untrusted input and is sanitised before being used in a
    filesystem path (CWE-22).  The resolved path must remain within
    ``_FP_BASE_DIR``.

    :param list_name: Logical name of the list (e.g. ``"cve_exclusions"``).
    :returns: Parsed list of false-positive entries.
    """
    # Strip any directory components from the caller-supplied name
    safe_name = Path(list_name).name
    fp_path = _safe_fp_path(f"{safe_name}.json")

    if not fp_path.exists():
        logger.warning("False-positive list not found: %s", fp_path)
        return []

    with fp_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {fp_path}, got {type(data).__name__}")

    logger.debug("Loaded %d false-positive entries from %s", len(data), fp_path)
    return data  # type: ignore[return-value]


def save_false_positive_list(list_name: str, entries: list[dict[str, Any]]) -> None:
    """Persist *entries* to a false-positive definition file.

    *list_name* is sanitised before constructing the target path to prevent
    path traversal (CWE-22).
    """
    safe_name = Path(list_name).name
    fp_path = _safe_fp_path(f"{safe_name}.json")

    fp_path.parent.mkdir(parents=True, exist_ok=True)
    with fp_path.open("w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2)

    logger.info("Saved %d false-positive entries to %s", len(entries), fp_path)


def is_false_positive(finding: dict[str, Any], fp_list: list[dict[str, Any]]) -> bool:
    """Return True if *finding* matches any entry in *fp_list*."""
    cve_id = finding.get("cve_id", "")
    package = finding.get("package", "")

    for entry in fp_list:
        if (
            entry.get("cve_id")
            and entry["cve_id"] == cve_id
            and (not entry.get("package") or entry["package"] == package)
        ):
            return True
    return False


def filter_false_positives(
    findings: list[dict[str, Any]],
    list_name: str,
) -> list[dict[str, Any]]:
    """Return *findings* with false-positive entries removed.

    Loads the suppression list identified by *list_name* (safely), then
    filters the supplied findings.
    """
    fp_list = load_false_positive_list(list_name)
    filtered = [f for f in findings if not is_false_positive(f, fp_list)]
    suppressed = len(findings) - len(filtered)
    if suppressed:
        logger.info("Suppressed %d false-positive finding(s)", suppressed)
    return filtered
