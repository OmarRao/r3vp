# Phase 3: Production Hardening

**Status:** Complete
**Release:** v0.3.0 (2026-06-15)

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/

## What was built

Phase 3 hardened the platform for production: notifications, access control, compliance reporting, and full AWS deployment automation.

## SLA breach notifications

When a test run completes and actual RTO or RPO exceeds the target, or the test fails outright, R3VP dispatches notifications automatically. Three channels supported:

- **Slack**: incoming webhook with colored attachment, workload name, breach details, run ID
- **Teams**: adaptive card via incoming webhook
- **Email**: AWS SES, branded R3VP email with breach summary

Notification channels are configured per-org via POST /v1/notifications. Each channel specifies which events to subscribe to: test_failed, rto_breach, rpo_breach.

## Role-based access control

Two roles: admin (full access) and viewer (read-only dashboards). Write endpoints - triggering tests, setting targets, managing notification channels, provisioning users - all require admin role. Alembic migration 0004 adds the role column to the users table with default admin.

## Audit log CSV export

GET /v1/audit-log/export streams a CSV of all audit events in a date range (max 90 days). Columns: occurred_at, event_type, actor_type, actor_id, resource_id, detail. Suitable for compliance reviews and cyber insurance submissions.

## Appliances portal

Dedicated /dashboard/appliances list shows all deployed appliances with color-coded status badges: green (heartbeat < 5 min), amber (5-30 min), red (>30 min or never). The detail page shows the mTLS thumbprint with copy-to-clipboard, workload count, and a deregister button with confirmation.

## Production Terraform

- **ECS Fargate**: task definition with all env vars from config, CPU auto-scaling 1-4 tasks at 70% threshold, CloudWatch logs
- **ALB**: HTTP-to-HTTPS redirect, HTTPS listener with TLS 1.3 policy, /health check every 30s
- **CloudFront**: no-cache for all /v1/* API paths (Authorization header forwarded), short 10s cache for /health, HTTPS-only origin

## Cyber insurance report

GET /v1/reports/cyber-insurance generates a formal PDF attestation document covering:
- Executive summary: tested workload count, pass rate, avg RTO, RTO/RPO compliance %
- NIST CSF Recover function mapping: RC.RP-1/2, RC.IM-1/2, RC.CO-3 with evidence descriptions
- Per-workload results table: test date, restore point age, RTO/RPO vs targets, pass/fail
- Formal attestation block with signature line

## Integration tests

Real Postgres tests using a session-scoped async engine:
- Inventory sync upsert idempotency: sync 2 VMs, re-sync with updated name, verify no duplicates
- Readiness score calculation: seed 3 workloads with known outcomes, verify compliance math
