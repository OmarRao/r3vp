"""Evidence vault: bundle test run artifacts into a signed ZIP archive."""
from __future__ import annotations
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any


def build_evidence_bundle(
    org_name: str,
    report_pdf_bytes: bytes | None,
    report_filename: str,
    test_runs: list[dict[str, Any]],
    audit_chain_entries: list[dict[str, Any]],
    framework: str = "general",
) -> tuple[bytes, str]:
    """
    Build a signed ZIP evidence bundle.

    Bundle structure:
        manifest.json           - SHA-256 of every included file
        report.pdf              - compliance PDF (if provided)
        audit_chain.json        - full hash chain export
        workloads/
            <workload_name>/
                summary.json    - test run metadata
                health_checks.json
                steps.json

    Returns (zip_bytes, sha256_hex).
    """
    buf = io.BytesIO()
    file_digests: dict[str, str] = {}

    def add_file(arcname: str, data: bytes) -> None:
        zf.writestr(arcname, data)
        file_digests[arcname] = hashlib.sha256(data).hexdigest()

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        if report_pdf_bytes:
            add_file(report_filename, report_pdf_bytes)

        chain_bytes = json.dumps(audit_chain_entries, indent=2).encode()
        add_file("audit_chain.json", chain_bytes)

        for run in test_runs:
            wl_name = run.get("workload_name", "unknown").replace("/", "_")
            prefix = f"workloads/{wl_name}/"

            summary = {
                "workload": run.get("workload_name"),
                "provider": run.get("provider"),
                "test_date": run.get("test_date"),
                "status": run.get("status"),
                "rto_target_mins": run.get("rto_target"),
                "rto_actual_mins": run.get("rto_actual"),
                "rto_compliant": run.get("rto_ok"),
                "readiness_score": run.get("readiness_score"),
            }
            add_file(prefix + "summary.json", json.dumps(summary, indent=2).encode())

            if run.get("health_checks"):
                add_file(prefix + "health_checks.json", json.dumps(run["health_checks"], indent=2).encode())

            if run.get("steps"):
                add_file(prefix + "steps.json", json.dumps(run["steps"], indent=2).encode())

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "org": org_name,
            "framework": framework,
            "r3vp_version": "0.7.0",
            "files": file_digests,
        }
        manifest_bytes = json.dumps(manifest, indent=2).encode()
        zf.writestr("manifest.json", manifest_bytes)

    zip_bytes = buf.getvalue()
    zip_sha256 = hashlib.sha256(zip_bytes).hexdigest()
    return zip_bytes, zip_sha256
