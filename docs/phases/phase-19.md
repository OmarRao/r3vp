# Phase 19: Live Demo Enhancements (Print Reports, Trends, Risk Heatmap, Alerting)

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 19 enhances the public interactive demo (`docs/demo.html`, served via GitHub Pages at
https://omarrao.github.io/r3vp/demo.html) with four capabilities that surface the platform's
reporting and analytics value without requiring a backend or login.

---

## Printable Compliance Reports

The compliance "Print Report" action now generates a fully formatted, print-ready report in a
new browser tab instead of a placeholder toast. The report mirrors the styling of the sample
report mockup (`docs/screenshots/mockup-reports.html`) and includes:

- Branded header with R3VP logo, report ID, generation date, organization, and reporting period
- Summary cards: overall score, RTO compliance, controls passing, workload count
- An attestation statement describing the evidence basis
- A control-by-control assessment table with per-control score and pass/partial status
- An evidence summary table (validated workloads, tests executed, average RTO/RPO, artifact count, audit-trail integrity)
- A footer with a generated SHA-256 signature line and author attribution

Reports are generated client-side for four frameworks, each with its own control set and scores:

| Framework | Controls | Overall | RTO Compliance |
|---|---|---|---|
| NIST CSF 2.0 | RC.RP-01/02/05, RC.CO-03, ID.RA-01, PR.IP-04, DE.CM-01 | 91% | 89% |
| ISO 27001:2022 | A.8.13, A.8.14, A.5.29, A.5.30, A.8.16 | 86% | 85% |
| SOC 2 Type II | CC7.5, CC9.1, A1.2, A1.3, CC6.8, CC4.1 | 89% | 85% |
| PCI DSS 4.0 | 12.10.1/2, 12.3.1, 10.7, 11.6 | 88% | 82% |

The generated tab includes a "Print / Save PDF" control that calls `window.print()`; the print
stylesheet hides the toolbar so the saved PDF contains only the report.

---

## Trends & Risk

A new "Trends & Risk" section provides longitudinal analytics:

- **RTO trend chart**: 12-week SVG line of average RTO achieved against the target SLA line
- **Readiness score trajectory**: 12-week SVG line with a projected 30-day target marker
- **KPI strip**: 90-day RTO trend (-27%), RPO trend (-34%), high-risk workload count, and readiness delta (+9)

### Risk Heatmap

A 3x5 heatmap plots business criticality (Tier 1/2/3) against days since last validation
(0-3, 4-7, 8-14, 15-30, 30+ days). Each cell is color-graded from low risk (green) to critical
(red) based on combined criticality and staleness, shows the workload count, and is clickable for
a drill-down toast. A legend maps the five risk bands.

---

## Alert Channels

The Continuous Validation section now documents the configured alert delivery channels:

| Channel | Destination | Triggers |
|---|---|---|
| Microsoft Teams | #dr-ops | Test failure, RTO breach, SLA miss |
| Slack | #recovery-alerts | Test failure, threat detected |
| Email | dr-team@contoso.com | Daily digest, weekly scorecard |
| PagerDuty | DR On-Call rotation | P1 incidents only |
| Webhook | SIEM endpoint (CEF) | All audit events |

---

## Files Changed

- `docs/demo.html`: added `printReport()` + `REPORT_DATA`, Trends & Risk section with `buildTrends()`
  and `buildHeatmap()`, alert channels card, and "Trends & Risk" nav item
- `.claude/launch.json`: added `r3vp-demo` static-server config for local preview

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
