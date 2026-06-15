# Phase 1: Foundation

**Status:** Complete
**Release:** v0.1.0 (2026-06-13)

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/

## What was built

Phase 1 established the full technical foundation of R3VP. Every component that later phases build on was designed and implemented here.

## Appliance

The on-premises appliance is a Python 3.12 Docker container that runs inside the customer network. It communicates outbound-only over mutual TLS - it never opens any inbound ports.

**Veeam connector** authenticates to the Veeam B&R REST API using OAuth2, auto-refreshes tokens, and provides methods to list backup jobs, list protected VMs, list restore points, and manage instant recovery sessions.

**vCenter connector** uses pyVmomi to connect to VMware vCenter, read VM inventory, provision isolated VLAN port groups, poll VMware Tools status, and capture console screenshots.

**SOPS vault** encrypts Veeam and vCenter credentials at rest using age encryption. The appliance decrypts them at startup. Plaintext credentials never leave the customer environment.

**Temporal workflow** orchestrates the 10-step recovery test: inventory sync, restore point selection, isolated network provisioning, instant recovery, VM boot wait, health checks, evidence capture, RTO/RPO measurement, result reporting, and teardown. Implemented as a saga so teardown always runs even if any step fails.

**Health checks** validate the recovered VM: WinRM for Windows OS status, SSH + systemctl for Linux, Active Directory LDAP bind, and stubs for SQL Server.

## SaaS API

FastAPI + SQLAlchemy async backend on PostgreSQL 16.

**Appliance relay channel**: authenticated via mTLS certificate thumbprint (not JWT). Endpoints: register, heartbeat, inventory sync, progress reporting, result reporting, evidence upload, command polling.

**Workload management**: org-scoped CRUD for discovered VMs, RTO/RPO targets.

**Test run management**: trigger, track, and report on recovery tests.

**Readiness scoring**: aggregate SQL queries producing overall score, RTO compliance %, RPO compliance %, and 90-day trend data.

**Auth0 JWT**: RS256 JWKS verification, org_id extracted from custom claim.

## Portal

Next.js 14 App Router portal with Auth0 login.

Dashboard shows readiness score gauge, tested/total workload count, RTO/RPO compliance percentages, 90-day trend chart, and workload table.

## Infrastructure

- Terraform modules for RDS PostgreSQL 16 (db.t4g.medium, encrypted, deletion protection) and S3 evidence bucket (versioning, KMS, 365-day lifecycle)
- GitHub Actions CI: lint, typecheck, unit tests, integration tests, Docker builds
- mTLS cert generation scripts for bash and PowerShell
