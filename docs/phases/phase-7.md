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

New page at `/dashboard/reports/schedule`:
- List of active delivery schedules with cron expression, recipients, last/next run, enable/disable toggle
- New Schedule form: name, framework, cadence (monthly/quarterly/weekly), coverage period, delivery channel and destination
- Delivery log showing per-recipient delivery status

Evidence vault view per org:
- Bundle history with SHA-256, file count, size, and download action
- Generate Bundle form with date range, framework, and include checkboxes
- Bundle contents tree showing manifest.json, report PDF, audit_chain.json, workloads/<name>/ subdirectories

---

## Scheduled Report Delivery

`ReportSchedule` model fields:

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| org_id | UUID | Owning org |
| name | VARCHAR(200) | Human label |
| report_type | VARCHAR(50) | soc2, iso27001, nist_csf, monthly_summary, cyber_insurance |
| cron | VARCHAR(100) | Standard 5-field cron expression |
| period_days | INTEGER | How many days back the report covers |
| recipients | JSONB | List of {type, destination} objects |
| enabled | BOOLEAN | Pause/resume without deleting |
| last_run_at | TIMESTAMPTZ | When delivery last ran |
| next_run_at | TIMESTAMPTZ | Computed next fire time |

**Temporal workflow:** `ReportScheduleWorkflow` in `apps/appliance/src/workflows/report_schedule_workflow.py`

1. `fetch_schedule_config` activity: fetches schedule from API, computes from/to dates
2. `generate_and_deliver_report` activity: POSTs to `/compliance/generate`, then calls `deliver_report()` for each recipient

**Delivery channels:** email (SMTP), Slack (incoming webhook), Teams (MessageCard webhook). Configured via `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` environment variables.

**Schedule API:**

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/report-schedules` | List org schedules |
| POST | `/api/v1/report-schedules` | Create schedule |
| PATCH | `/api/v1/report-schedules/{id}/toggle` | Enable or disable |
| DELETE | `/api/v1/report-schedules/{id}` | Delete |

---

## Evidence Vault

Each bundle is a deflate-compressed ZIP containing:

```
r3vp-evidence-<framework>-<from>-<to>.zip
├── manifest.json          SHA-256 of every file
├── r3vp-<framework>-....pdf
├── audit_chain.json       full hash chain export
└── workloads/
    ├── <workload-name>/
    │   ├── summary.json   RTO target vs actual, provider, status
    │   ├── steps.json     7-step workflow with durations
    │   └── health_checks.json
    └── ...
```

The entire ZIP is SHA-256 hashed after assembly. The digest is returned in the `X-SHA256` response header and stored in the `evidence_bundles` table. Recipients can verify the bundle has not been modified by recomputing the digest.

**API:**

```
POST /api/v1/reports/evidence-bundle
  ?from_date=2026-05-01
  &to_date=2026-05-31
  &framework=soc2
```

Response: `application/zip` with headers:
- `Content-Disposition: attachment; filename="r3vp-evidence-soc2-2026-05-01-2026-05-31.zip"`
- `X-SHA256: <hex>`
- `X-File-Count: <n>`

---

## Database Migration 0009

```sql
CREATE TABLE report_schedules (
    id            UUID PRIMARY KEY,
    org_id        UUID NOT NULL,
    name          VARCHAR(200) NOT NULL,
    report_type   VARCHAR(50) NOT NULL,
    cron          VARCHAR(100) NOT NULL,
    period_days   INTEGER DEFAULT 30,
    recipients    JSONB DEFAULT '[]',
    enabled       BOOLEAN DEFAULT true,
    last_run_at   TIMESTAMPTZ,
    next_run_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now(),
    created_by    UUID REFERENCES users(id)
);

CREATE TABLE evidence_bundles (
    id          UUID PRIMARY KEY,
    org_id      UUID NOT NULL,
    report_id   UUID REFERENCES compliance_reports(id),
    from_date   VARCHAR(10) NOT NULL,
    to_date     VARCHAR(10) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    sha256      VARCHAR(64),
    file_count  INTEGER DEFAULT 0,
    size_bytes  INTEGER DEFAULT 0
);
```

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
