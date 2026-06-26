"""Compliance report generation service."""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Base directory for report storage -- all paths are validated to stay within this root
_REPORTS_BASE_DIR = Path(os.environ.get("R3VP_REPORTS_DIR", "/var/r3vp/reports")).resolve()


def _sanitize_storage_path(relative_path: str) -> Path:
    """Resolve and validate that a storage path stays within the reports base directory."""
    resolved = (_REPORTS_BASE_DIR / relative_path).resolve()
    if not str(resolved).startswith(str(_REPORTS_BASE_DIR)):
        raise ValueError(f"Path traversal detected: {relative_path!r} resolves outside reports directory")
    return resolved


def _redact_sensitive_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* with credential-like values replaced by a redaction marker."""
    sensitive_keys = re.compile(
        r"(password|passwd|secret|token|api_key|apikey|credential|auth|bearer)",
        re.IGNORECASE,
    )
    redacted = {}
    for key, value in data.items():
        if sensitive_keys.search(key):
            redacted[key] = "**REDACTED**"
        elif isinstance(value, dict):
            redacted[key] = _redact_sensitive_fields(value)
        else:
            redacted[key] = value
    return redacted


def build_report_summary(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Build a sanitised summary dict suitable for persistent storage.

    Sensitive fields are redacted before the summary is written so that
    credentials never appear in the database (CWE-312).
    """
    sanitized = _redact_sensitive_fields(raw_data)
    logger.debug("Built report summary with %d top-level keys", len(sanitized))
    return sanitized


def compute_report_checksum(pdf_bytes: bytes) -> str:
    """Return the SHA-256 hex digest of the given PDF bytes."""
    return hashlib.sha256(pdf_bytes).hexdigest()


def resolve_report_path(org_id: str, filename: str) -> Path:
    """Resolve a safe absolute path for a report file.

    Raises ValueError if the resolved path would escape the reports base dir.
    Both *org_id* and *filename* are treated as untrusted input and are
    validated before being joined into a filesystem path (CWE-22).
    """
    # Strip any leading separators / dotdot components from the individual segments
    safe_org = Path(org_id).name
    safe_filename = Path(filename).name
    relative = Path(safe_org) / safe_filename
    return _sanitize_storage_path(str(relative))


def write_report_file(org_id: str, filename: str, content: bytes) -> Path:
    """Write *content* to a validated path under the reports base directory.

    Returns the resolved Path that was written.
    """
    dest = resolve_report_path(org_id, filename)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    logger.info("Wrote report file: %s (%d bytes)", dest, len(content))
    return dest
