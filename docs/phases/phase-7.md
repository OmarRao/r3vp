# Phase 7: Compliance and Reporting

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 7 adds enterprise-grade compliance reporting to R3VP. Every recovery validation test run now generates audit evidence that maps directly to security control frameworks required by enterprise InfoSec teams, auditors, and cyber insurance underwriters.

Three things ship in this phase:

1. **Signed compliance PDF reports** for SOC 2 Type II, ISO 27001:2022, NIST CSF 2.0, and cyber insurance
2. **Hash-chained audit trail** in the appliance for tamper-evident evidence
3. **Report history** with SHA-256 digest per PDF, persisted in PostgreSQL

---

## Compliance Frameworks Supported

### SOC 2 Type II
Controls mapped from recovery test data:
| Control | Title | How R3VP Satisfies It |
|---|---|---|
| CC7.5 | Recovery Testing | Automated recovery tests with pass/fail evidence per workload |
| CC9.1 | Risk Mitigation | RTO compliance measurement against defined targets |
| A1.3 | Availability Recovery | Actual RTO vs target tracked for each test run |

### ISO/IEC 27001:2022
| Control | Title | How R3VP Satisfies It |
|---|---|---|
| A.8.13 | Information Backup | Verifies restore points are accessible and restorable |
| A.8.14 | Redundancy of Facilities | Multi-provider coverage across 10 platforms |
| A.5.29 | Security During Disruption | Validates recovery capability during simulated incidents |
| A.5.30 | ICT Readiness | Continuous RTO measurement and trend tracking |

### NIST Cybersecurity Framework 2.0
| Control | Title | How R3VP Satisfies It |
|---|---|---|
| RC.RP-01 | Recovery Plan Execution | Full saga workflow execution per test run |
| RC.RP-02 | Recovery Actions | Workload prioritization and restore point selection |
| RC.RP-05 | Backup Integrity Verification | Restore point validity confirmed before each test |
| ID.RA-01 | Vulnerability Identification | Threat scanner cross-references active findings |

---

## Hash-Chained Audit Trail

The R3VP appliance maintains a local SQLite audit log where each entry is hash-chained to the previous, making tampering detectable.

**Chain formula:**
```
entry_hash = SHA-256(prev_hash + timestamp + event_type + json(payload))
```

The first entry uses `"0" * 64` as the genesis prev_hash. Any insertion, deletion, or modification of a record breaks the chain and is detected by the verify endpoint.

**Events logged:**
- `test_run.started`
- `test_run.step.completed`
- `test_run.completed`
- `test_run.failed`
- `health_check.result`
- `evidence.captured`
- `threat.detected`
- `report.generated`

**Appliance module:** `apps/appliance/src/audit/chain.py`

Chain export is included in every compliance PDF report as an appendix reference. The API exposes `/audit/chain/verify` to confirm chain integrity on demand.

---

## PDF Report Structure

Each generated PDF includes:

1. Cover: organization name, framework, reporting period, generation timestamp
2. Executive summary: KPI row with total runs, pass rate, RTO compliance, controls passing
3. Control assessment table: each framework control with PASS/FAIL and evidence citation
4. Test run detail table: every workload tested in the period with RTO target vs actual
5. Cryptographic signature block: SHA-256 digest, generation timestamp, R3VP version

PDF bytes are SHA-256 hashed after generation. The hex digest is stored in `compliance_reports.sha256` and returned in the `X-SHA256` response header. Recipients can verify the PDF has not been modified since generation.

---

## API Endpoints

All endpoints require a valid Auth0 JWT with `org_id` claim.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/reports/compliance/frameworks` | List supported frameworks and control mappings |
| POST | `/api/v1/reports/compliance/generate` | Generate and download a compliance PDF |
| GET | `/api/v1/reports/compliance/history` | List previously generated reports |
| GET | `/api/v1/reports/cyber-insurance` | Generate cyber insurance evidence bundle (existing) |
| GET | `/api/v1/audit` | List audit events with pagination |
| GET | `/api/v1/audit/export` | Export audit events as CSV |
| GET | `/api/v1/audit/chain/verify` | Verify appliance hash chain integrity |

### Generate compliance report

```
POST /api/v1/reports/compliance/generate
  ?report_type=soc2
  &from_date=2026-05-01
  &to_date=2026-05-31
```

Response: `application/pdf` with headers:
- `Content-Disposition: attachment; filename="r3vp-soc2-2026-05-01-2026-05-31.pdf"`
- `X-Report-ID: <uuid>`
- `X-SHA256: <hex>`

---

## Database Migration

Migration `0008_compliance_reports` adds:

```sql
CREATE TABLE compliance_reports (
    id            UUID PRIMARY KEY,
    org_id        UUID NOT NULL,
    report_type   VARCHAR(50) NOT NULL,
    from_date     VARCHAR(10) NOT NULL,
    to_date       VARCHAR(10) NOT NULL,
    generated_at  TIMESTAMPTZ DEFAULT now(),
    generated_by  UUID REFERENCES users(id),
    status        VARCHAR(20) DEFAULT 'generating',
    sha256        VARCHAR(64),
    storage_path  VARCHAR(512),
    summary       JSONB DEFAULT '{}'
);
```

---

## Dependencies Added

```toml
# apps/api/pyproject.toml
weasyprint = ">=62.0"   # already present from prior phase
jinja2 = ">=3.1"        # already present
```

No new appliance dependencies. The audit chain module uses Python stdlib only (hashlib, sqlite3, json).

---

## Portal

New page at `/dashboard/reports`:
- Framework selector (SOC 2, ISO 27001, NIST CSF, Monthly Summary, Cyber Insurance)
- Date range picker
- Generate PDF button (calls API, triggers browser download)
- Report history table with download and view actions
- Audit trail preview with chain integrity status

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
