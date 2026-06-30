# Phase 20: Portal Reports + Risk Heatmap, Scheduled Report Delivery, PagerDuty/Webhook Alerting

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 20 brings the live-demo features into the real Next.js portal, fills a gap in the
backend scheduler so scheduled compliance reports actually fire, adds two new alert delivery
channels, and clears pre-existing type and dependency issues that were blocking the build and
test suite.

---

## Portal (apps/portal)

### Printable Compliance Reports
`app/dashboard/reports/page.tsx` now generates a fully formatted, print-ready report in a new
tab when "Generate PDF" is clicked, matching the live-demo layout (branded header, summary
cards, per-control assessment table, evidence summary, signed footer). Four frameworks are
covered (SOC 2 Type II, ISO 27001:2022, NIST CSF 2.0, Monthly Summary, Cyber Insurance), each
with its own control set. The generated tab includes a Print / Save PDF control.

### Risk Heatmap
`app/dashboard/insights/page.tsx` adds a graphical risk heatmap above the existing risk-ranking
table: business criticality (Tier 1/2/3) versus days since last validation (0-3, 4-7, 8-14,
15-30, 30+ days), with cells color-graded from low risk (green) to critical (red), workload
counts, hover detail, and a five-band legend. The existing ranking table is unchanged.

---

## Backend (apps/api)

### Scheduled Report Delivery
`src/scheduler.py` previously registered APScheduler jobs only for workload test-run crons.
It now also loads enabled `ReportSchedule` rows and registers a cron job per schedule. When a
schedule fires, `_run_report_schedule` computes the reporting window, dispatches delivery
notifications to the configured recipients, and updates `last_run_at` / `next_run_at` (next run
computed via APScheduler's own `CronTrigger`, so no new dependency).

### PagerDuty and Webhook Alert Channels
`src/services/notifications.py` adds two channel types to the dispatcher:
- `pagerduty`: triggers an incident via the PagerDuty Events API v2 (destination is the routing key)
- `webhook`: POSTs a generic R3VP JSON payload to an arbitrary URL (e.g. SIEM ingest)

A new `send_report_delivery()` helper notifies report-schedule recipients (email, Slack, Teams,
webhook) when a scheduled report is generated.

---

## Fixes (unblocking build and tests)

- Added `python-multipart` to API dependencies. FastAPI's evidence-upload route requires it; its
  absence was preventing the app from importing in a clean environment (and blocking the test suite).
- Fixed a `SyntaxError` in `src/services/executive_report.py` (backslash-escaped quotes inside an
  f-string expression) that broke app import.
- Resolved three pre-existing portal type errors that were failing CI's `pnpm type-check`:
  typed-route casts in `components/breadcrumb.tsx` and `app/dashboard/providers/page.tsx`, and a
  custom-event overload cast in `lib/track.ts`.
- Pinned `sops` to `v3.13.1` in the appliance Dockerfile (was fetching `latest`) for reproducible builds.

---

## Tests

`apps/api/tests/test_auth_jwt.py` adds coverage for:
- The PyJWT migration: the auth module uses PyJWT (not python-jose), invalid tokens raise 401, and
  a correctly signed RS256 token decodes to its claims.
- The new PagerDuty sender (posts a trigger event to the Events API v2) and the generic webhook
  sender (posts an R3VP JSON payload to the configured URL).

Full API unit suite passes (7 tests).

---

## Deferred (require live systems, not faked)

- Real Veeam B&R / vCenter connector implementations (need live infrastructure to build and verify)
- SSO via Azure AD / Okta (needs a real IdP to validate the flow end to end)
- Full portal dark mode (every page uses hardcoded light Tailwind classes; a partial pass would
  look broken, so this is reserved for a dedicated complete effort)
- Video walkthrough in the README

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
