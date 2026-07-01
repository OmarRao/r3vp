"""Dependency vulnerability scanner using NVD/OSV feeds."""
from __future__ import annotations

import logging
from typing import Any

# Always use defusedxml to parse untrusted NVD/OSV feeds; it hardens against
# XML External Entity (XXE) injection and entity-expansion bombs (CWE-611).
# defusedxml is a declared dependency, so the vulnerable stdlib xml parser is
# never imported here.
import defusedxml.ElementTree as ET  # type: ignore[import]

logger = logging.getLogger(__name__)


def _parse_nvd_xml(xml_content: str) -> list[dict[str, Any]]:
    """Parse NVD CVE feed XML and return a list of vulnerability dicts.

    Uses ``defusedxml`` to prevent XML External Entity (XXE) attacks and
    entity-expansion bombs (CWE-611).
    """
    root = ET.fromstring(xml_content)
    entries: list[dict[str, Any]] = []

    for entry in root.iter("{http://scap.nist.gov/schema/feed/vulnerability/2.0}entry"):
        cve_id = entry.get("id", "")
        summary_el = entry.find(
            "{http://scap.nist.gov/schema/vulnerability/0.4}summary"
        )
        summary = summary_el.text if summary_el is not None else ""

        cvss_el = entry.find(
            ".//{http://scap.nist.gov/schema/vulnerability/0.4}score"
        )
        score_text = cvss_el.text if cvss_el is not None else "0.0"
        try:
            score = float(score_text or "0.0")
        except ValueError:
            score = 0.0

        entries.append({"cve_id": cve_id, "summary": summary, "cvss_score": score})

    logger.debug("Parsed %d CVE entries from NVD XML feed", len(entries))
    return entries


def _parse_cyclonedx_sbom(xml_content: str) -> list[dict[str, Any]]:
    """Parse a CycloneDX SBOM in XML format.

    Uses a safe parser to prevent XXE injection (CWE-611).
    """
    root = ET.fromstring(xml_content)
    ns = "http://cyclonedx.org/schema/bom/1.4"
    components: list[dict[str, Any]] = []

    for comp in root.iter(f"{{{ns}}}component"):
        name_el = comp.find(f"{{{ns}}}name")
        version_el = comp.find(f"{{{ns}}}version")
        purl_el = comp.find(f"{{{ns}}}purl")
        components.append(
            {
                "name": name_el.text if name_el is not None else "",
                "version": version_el.text if version_el is not None else "",
                "purl": purl_el.text if purl_el is not None else "",
            }
        )

    logger.debug("Parsed %d components from CycloneDX SBOM", len(components))
    return components


def scan_dependencies(sbom_xml: str, nvd_feed_xml: str) -> list[dict[str, Any]]:
    """Cross-reference SBOM components against NVD feed and return matching CVEs.

    Both XML inputs are parsed with XXE-safe parsers (CWE-611).
    """
    components = _parse_cyclonedx_sbom(sbom_xml)
    vulnerabilities = _parse_nvd_xml(nvd_feed_xml)

    # Build a simple name-based lookup (real implementation would use purl/CPE matching)
    comp_names = {c["name"].lower() for c in components}
    matches: list[dict[str, Any]] = []

    for vuln in vulnerabilities:
        summary_lower = vuln.get("summary", "").lower()
        for name in comp_names:
            if name and name in summary_lower:
                matches.append({**vuln, "matched_component": name})
                break

    logger.info(
        "Dependency scan complete: %d component(s), %d match(es)",
        len(components),
        len(matches),
    )
    return matches
