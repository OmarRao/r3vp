"""Custom compliance framework evaluation engine."""
from __future__ import annotations

from typing import Any

BUILTIN_FRAMEWORKS = [
    {
        "short_code": "SOC2",
        "name": "SOC 2 Type II",
        "version": "2017",
        "description": "AICPA Service Organization Control 2 Type II - Trust Services Criteria",
        "controls": [
            {"control_id": "CC7.5", "title": "Recovery Testing", "category": "Availability", "r3vp_metric": "pass_rate", "pass_threshold": 95, "r3vp_evidence_types": ["test_run_pass", "health_check"]},
            {"control_id": "CC9.1", "title": "Risk Mitigation - Recovery", "category": "Risk Management", "r3vp_metric": "coverage_pct", "pass_threshold": 100, "r3vp_evidence_types": ["evidence_bundle"]},
            {"control_id": "A1.3", "title": "Availability Recovery", "category": "Availability", "r3vp_metric": "rto_compliance", "pass_threshold": 90, "r3vp_evidence_types": ["rto_measurement"]},
        ],
    },
    {
        "short_code": "ISO27001",
        "name": "ISO/IEC 27001:2022",
        "version": "2022",
        "description": "Information security management systems - Requirements and controls",
        "controls": [
            {"control_id": "A.8.13", "title": "Information Backup", "category": "Technology Controls", "r3vp_metric": "coverage_pct", "pass_threshold": 100, "r3vp_evidence_types": ["evidence_bundle"]},
            {"control_id": "A.8.14", "title": "Redundancy of Information Processing Facilities", "category": "Technology Controls", "r3vp_metric": "pass_rate", "pass_threshold": 90, "r3vp_evidence_types": ["test_run_pass"]},
            {"control_id": "A.5.29", "title": "Information Security During Disruption", "category": "Organizational Controls", "r3vp_metric": "rto_compliance", "pass_threshold": 85, "r3vp_evidence_types": ["rto_measurement", "health_check"]},
            {"control_id": "A.5.30", "title": "ICT Readiness for Business Continuity", "category": "Organizational Controls", "r3vp_metric": "pass_rate", "pass_threshold": 95, "r3vp_evidence_types": ["test_run_pass", "audit_chain"]},
        ],
    },
    {
        "short_code": "NIST-CSF",
        "name": "NIST Cybersecurity Framework 2.0",
        "version": "2.0",
        "description": "NIST CSF 2.0 - Recover function controls for recovery planning and improvements",
        "controls": [
            {"control_id": "RC.RP-01", "title": "Recovery Plan Execution", "category": "Recover", "r3vp_metric": "pass_rate", "pass_threshold": 90, "r3vp_evidence_types": ["test_run_pass"]},
            {"control_id": "RC.RP-02", "title": "Recovery Actions Documented", "category": "Recover", "r3vp_metric": "coverage_pct", "pass_threshold": 80, "r3vp_evidence_types": ["evidence_bundle"]},
            {"control_id": "RC.RP-05", "title": "Backup Integrity Verification", "category": "Recover", "r3vp_metric": "rto_compliance", "pass_threshold": 85, "r3vp_evidence_types": ["rto_measurement", "health_check"]},
        ],
    },
    {
        "short_code": "DORA",
        "name": "EU Digital Operational Resilience Act",
        "version": "2025",
        "description": "DORA Article 11 - ICT Business Continuity Policy and Testing requirements for EU financial entities",
        "controls": [
            {"control_id": "Art.11(b)", "title": "ICT Continuity Plans - Backup Testing", "category": "ICT Business Continuity", "r3vp_metric": "pass_rate", "pass_threshold": 95, "r3vp_evidence_types": ["test_run_pass", "evidence_bundle"]},
            {"control_id": "Art.11(f)", "title": "Recovery Testing - Periodic Execution", "category": "ICT Business Continuity", "r3vp_metric": "coverage_pct", "pass_threshold": 100, "r3vp_evidence_types": ["test_run_pass"]},
            {"control_id": "Art.12(1)", "title": "ICT-Related Incident Response - RTO", "category": "ICT Incident Management", "r3vp_metric": "rto_compliance", "pass_threshold": 95, "r3vp_evidence_types": ["rto_measurement"]},
            {"control_id": "Art.25(1)", "title": "TLPT - Advanced Testing Evidence", "category": "Digital Operational Resilience Testing", "r3vp_metric": "pass_rate", "pass_threshold": 100, "r3vp_evidence_types": ["test_run_pass", "health_check", "audit_chain"]},
        ],
    },
    {
        "short_code": "PCI-DSS",
        "name": "PCI DSS 4.0",
        "version": "4.0",
        "description": "Payment Card Industry Data Security Standard v4.0 - Requirements for backup and recovery testing",
        "controls": [
            {"control_id": "Req 12.3.4", "title": "Hardware and Software Technologies Reviewed", "category": "Security Policy", "r3vp_metric": "coverage_pct", "pass_threshold": 100, "r3vp_evidence_types": ["evidence_bundle"]},
            {"control_id": "Req 12.10.1", "title": "Incident Response Plan - Recovery Testing", "category": "Incident Response", "r3vp_metric": "pass_rate", "pass_threshold": 90, "r3vp_evidence_types": ["test_run_pass"]},
        ],
    },
    {
        "short_code": "HIPAA",
        "name": "HIPAA Security Rule",
        "version": "2024",
        "description": "HIPAA Security Rule - Administrative safeguards for contingency planning and disaster recovery",
        "controls": [
            {"control_id": "§164.308(a)(7)(i)", "title": "Contingency Plan - Data Backup", "category": "Administrative Safeguards", "r3vp_metric": "coverage_pct", "pass_threshold": 100, "r3vp_evidence_types": ["evidence_bundle"]},
            {"control_id": "§164.308(a)(7)(ii)(B)", "title": "Disaster Recovery Plan - Testing", "category": "Administrative Safeguards", "r3vp_metric": "pass_rate", "pass_threshold": 90, "r3vp_evidence_types": ["test_run_pass", "health_check"]},
            {"control_id": "§164.308(a)(7)(ii)(D)", "title": "Testing and Revision Procedures", "category": "Administrative Safeguards", "r3vp_metric": "rto_compliance", "pass_threshold": 85, "r3vp_evidence_types": ["rto_measurement"]},
        ],
    },
]

R3VP_METRICS = {
    "pass_rate": "Percentage of recovery tests that passed in the period",
    "rto_compliance": "Percentage of tests where actual RTO was within the target",
    "coverage_pct": "Percentage of workloads that have been tested at least once",
}

R3VP_EVIDENCE_TYPES = [
    "test_run_pass",
    "rto_measurement",
    "health_check",
    "audit_chain",
    "evidence_bundle",
]


def evaluate_framework(
    framework_controls: list[dict[str, Any]],
    pass_rate: float,
    rto_compliance: float,
    coverage_pct: float,
) -> dict[str, Any]:
    metrics = {
        "pass_rate": pass_rate,
        "rto_compliance": rto_compliance,
        "coverage_pct": coverage_pct,
    }

    results: dict[str, Any] = {}
    total_weight = 0
    weighted_pass = 0.0

    for ctrl in framework_controls:
        metric_name = ctrl.get("r3vp_metric")
        threshold = ctrl.get("pass_threshold", 0) or 0
        weight = ctrl.get("weight", 1) or 1
        actual = metrics.get(metric_name or "", 0.0)
        passing = actual >= threshold
        results[ctrl["control_id"]] = {
            "status": "pass" if passing else "fail",
            "metric": metric_name,
            "actual": round(actual, 1),
            "threshold": threshold,
            "weight": weight,
        }
        total_weight += weight
        if passing:
            weighted_pass += weight

    overall = round((weighted_pass / total_weight * 100) if total_weight else 0)
    controls_passing = sum(1 for r in results.values() if r["status"] == "pass")

    return {
        "overall_score": overall,
        "controls_assessed": len(framework_controls),
        "controls_passing": controls_passing,
        "control_results": results,
    }
