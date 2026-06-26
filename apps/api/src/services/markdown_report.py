"""Markdown report rendering for compliance summaries."""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api_key|apikey|credential|auth|bearer)",
    re.IGNORECASE,
)


def _redact_value(key: str, value: Any) -> Any:
    """Return a redacted placeholder if *key* looks like a credential field."""
    if _SENSITIVE_KEY_RE.search(key):
        return "**REDACTED**"
    if isinstance(value, dict):
        return {k: _redact_value(k, v) for k, v in value.items()}
    return value


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Strip sensitive values from metadata before embedding in a report.

    Prevents clear-text storage of credentials in Markdown output (CWE-312).
    """
    return {k: _redact_value(k, v) for k, v in metadata.items()}


def render_summary_section(title: str, items: list[dict[str, Any]]) -> str:
    """Render a Markdown section with a heading and a table of sanitised items."""
    lines: list[str] = [f"## {title}", ""]
    if not items:
        lines.append("_No items to display._")
        lines.append("")
        return "\n".join(lines)

    # Collect all keys across items then build a header row
    all_keys: list[str] = []
    for item in items:
        for k in item:
            if k not in all_keys:
                all_keys.append(k)

    lines.append("| " + " | ".join(all_keys) + " |")
    lines.append("| " + " | ".join(["---"] * len(all_keys)) + " |")

    for item in items:
        safe = _safe_metadata(item)
        row = " | ".join(str(safe.get(k, "")) for k in all_keys)
        lines.append(f"| {row} |")

    lines.append("")
    return "\n".join(lines)


def render_markdown_report(
    report_title: str,
    metadata: dict[str, Any],
    sections: list[dict[str, Any]],
) -> str:
    """Render a full Markdown compliance report.

    Sensitive fields in *metadata* are redacted before being written to the
    document so credentials are never stored in clear text (CWE-312).

    :param report_title: Human-readable title for the report.
    :param metadata: Arbitrary key/value pairs to display in the report header.
    :param sections: List of dicts with keys ``title`` (str) and ``items``
                     (list of dicts), one per section.
    :returns: Rendered Markdown string.
    """
    safe_meta = _safe_metadata(metadata)
    lines: list[str] = [f"# {report_title}", ""]

    if safe_meta:
        lines.append("## Report Metadata")
        lines.append("")
        for k, v in safe_meta.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    for section in sections:
        title = section.get("title", "Untitled")
        items = section.get("items", [])
        lines.append(render_summary_section(title, items))

    return "\n".join(lines)
