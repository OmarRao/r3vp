# Phase 22: Ransomware Threat Analysis Engine

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 22 adds the backend that analyzes backup restore points for ransomware
indicators before a recovery test, and picks the newest clean restore point.
Previously the platform stored appliance-submitted scan results but had no
engine to reason over restore-point metadata; the demo's "scan backup chains
for ransomware indicators" story had no implementation.

## Analysis Engine

`src/services/threat_analysis.py` (pure, unit-tested) detects:

| Indicator | Signal | Severity | MITRE |
|---|---|---|---|
| `entropy_anomaly` | average file entropy at/near the 8.0 ceiling (>= 7.9) | high | T1486 |
| `entropy_spike` | entropy jump >= 1.5 vs the rolling median of prior restore points | medium | T1486 |
| `mass_file_rename` | >= 25% of files renamed within one restore-point interval | high | T1486 |
| `ransomware_extension` | newly-seen extensions match known families (locky, ryuk, lockbit, conti, ...) | critical | T1486 |

`analyze_restore_points` returns per-point indicators, the highest severity, and
an `is_clean` flag (no high/critical indicator). `select_clean_restore_point`
returns the newest clean restore point, or None if every point is flagged.

## API

`POST /v1/threat-intel/analyze-restore-points` accepts a list of restore-point
metadata objects (id, created_at, avg_entropy, total_files, renamed_files,
new_extensions) that the appliance derives locally, and returns the per-point
analysis, the total indicators found, the flagged count, and the recommended
clean restore point. It is stateless and gated by the `threats:read` permission;
only derived metadata is sent, never backup content.

## Fix

All authenticated `/v1/threat-intel/*` endpoints declared auth as
`user: CurrentUser = Depends(AuthUser)`. Because `AuthUser` is an `Annotated`
alias (not a plain callable), FastAPI mis-introspected the dependency as
`*args/**kwargs` and returned 422 for every request. Switching to the
`user: AuthUser` idiom fixed all five endpoints (findings, incidents, incident
detail, resolve, scans). This mirrors the RBAC permissions fix in Phase 21:
authenticated surfaces that had never been exercised end to end were broken.

## Testing

- Unit tests (`tests/test_threat_analysis.py`): extension matching, each
  indicator type, clean-restore-point selection (newest unflagged, or None when
  all flagged), entropy-spike vs baseline, the endpoint happy path, and the
  permission-denied (403) path.
- 23 API unit tests pass; ruff clean.

## Follow-up

The appliance side derives the restore-point metadata (entropy sampling, rename
detection) against a live Veeam repository; that collection path is lab-gated
like the rest of ADR-003.

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
