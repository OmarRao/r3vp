# Phase 17: Custom Compliance Framework Builder

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 17 extends R3VP compliance reporting beyond the three built-in frameworks (SOC 2, ISO 27001, NIST CSF) to support any regulatory or internal framework. Organizations can define custom frameworks by mapping control IDs to R3VP metrics, then run automated assessments that score each control against live test data.

Six frameworks now ship out of the box: SOC 2 Type II, ISO/IEC 27001:2022, NIST CSF 2.0, EU DORA, PCI DSS 4.0, and HIPAA Security Rule.

---

## Built-in Frameworks

| Short Code | Name | Controls |
|---|---|---|
| SOC2 | SOC 2 Type II | CC7.5, CC9.1, A1.3 |
| ISO27001 | ISO/IEC 27001:2022 | A.8.13, A.8.14, A.5.29, A.5.30 |
| NIST-CSF | NIST Cybersecurity Framework 2.0 | RC.RP-01, RC.RP-02, RC.RP-05 |
| DORA | EU Digital Operational Resilience Act | Art.11(b), Art.11(f), Art.12(1), Art.25(1) |
| PCI-DSS | PCI DSS 4.0 | Req 12.3.4, Req 12.10.1 |
| HIPAA | HIPAA Security Rule | 164.308(a)(7)(i), (ii)(B), (ii)(D) |

---

## Custom Framework Builder

To create a custom framework:

1. `POST /v1/compliance-frameworks` with name and short_code (e.g. "MAS-TRM", "FCA-SYSC")
2. `POST /v1/compliance-frameworks/{id}/controls` for each control, mapping to one of three R3VP metrics
3. `POST /v1/compliance-frameworks/assess` to score the framework against the current period's test data

---

## R3VP Metrics

Each control maps to one of three measurable dimensions from R3VP test data:

| Metric | Description |
|---|---|
| pass_rate | Percentage of recovery tests that passed in the period |
| rto_compliance | Percentage of tests where actual RTO was within the target |
| coverage_pct | Percentage of workloads that have been tested at least once |

---

## Assessment Engine

`evaluate_framework()` scores each control independently:

1. Reads the control's `r3vp_metric` and `pass_threshold`
2. Compares the actual metric value to the threshold
3. Returns `pass` or `fail` per control with actual vs threshold values
4. Computes a weighted overall score (0-100) from control weights

The result is stored as a `FrameworkAssessment` record for historical comparison.

---

## Evidence Types

Controls declare which R3VP artifact types satisfy the requirement:

- `test_run_pass` - Completed recovery test with passing status
- `rto_measurement` - Measured actual RTO vs target
- `health_check` - Post-recovery application health check results
- `audit_chain` - SHA-256 hash-chained audit trail
- `evidence_bundle` - Signed ZIP containing all artifacts

---

## API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/v1/compliance-frameworks/catalog` | none | Built-in framework catalog |
| GET | `/v1/compliance-frameworks/metrics` | none | Available R3VP metrics |
| GET | `/v1/compliance-frameworks/evidence-types` | none | Available evidence types |
| GET | `/v1/compliance-frameworks` | reports:read | All frameworks (built-in + custom) |
| POST | `/v1/compliance-frameworks` | reports:write | Create custom framework |
| GET | `/v1/compliance-frameworks/{id}/controls` | reports:read | List controls for a framework |
| POST | `/v1/compliance-frameworks/{id}/controls` | reports:write | Add control to custom framework |
| POST | `/v1/compliance-frameworks/assess` | reports:write | Run assessment and store result |

---

## Database Migration 0018

Three tables:
- `compliance_frameworks`: org-scoped custom frameworks with short_code, version, and is_builtin flag
- `compliance_controls`: per-framework control definitions with metric mapping, threshold, weight, and evidence type list
- `framework_assessments`: scored assessment records with per-control results JSONB, overall score, and period range

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
