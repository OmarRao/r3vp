# Changelog

All notable changes to R3VP are documented here.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## [Unreleased] - Phase 18: Continuous Validation Mode

### Added
- ContinuousValidationPolicy model with configurable interval (minimum 1 min), workload scope, per-check toggles, and consecutive-failure alert threshold
- Six micro-check types: restore_point_freshness, mount_check, veeam_job_status, agent_heartbeat, vcenter_connectivity, rpo_compliance
- MicroValidationRun model recording per-check JSONB results, restore point age, duration, and alert_sent flag per run
- ValidationAlert model with alert_type, severity, resolution tracking, and cascade delete on policy removal
- Rolling health computation from last 100 runs: healthy (>=90% pass), degraded (70-89%), failing (<70%)
- Consecutive failure counter for alert escalation
- Policy toggle endpoint (PATCH /policies/{id}/toggle) for enable/disable without deletion
- Continuous Validation portal page with KPI row, policy cards, active alerts with severity borders, and runs table
- Available checks reference grid with category and description for each of the 6 check types
- Migration 0019 adding continuous_validation_policies, micro_validation_runs, validation_alerts tables

---

## [Unreleased] - Phase 17: Custom Compliance Framework Builder

### Added
- Six compliance frameworks now built-in: SOC 2 Type II, ISO/IEC 27001:2022, NIST CSF 2.0, EU DORA (Article 11/12/25), PCI DSS 4.0, HIPAA Security Rule
- ComplianceFramework model for org-scoped custom frameworks with short_code, version, and is_builtin flag
- ComplianceControl model mapping control IDs to R3VP metrics (pass_rate, rto_compliance, coverage_pct) with thresholds and weights
- FrameworkAssessment model storing scored results per control in JSONB with overall weighted score and period range
- evaluate_framework() engine: scores each control against live metric values, computes weighted 0-100 overall score
- Framework catalog endpoint listing all built-in frameworks with control counts
- Custom framework CRUD: create framework, add controls, list controls
- Assessment endpoint running scoring against current period metrics and persisting result
- Framework builder portal page: 6 framework cards with DORA highlighted as EU mandate, 3-step custom builder flow
- Migration 0018 adding compliance_frameworks, compliance_controls, framework_assessments tables

---

## [Unreleased] - Phase 16: MSSP Console

### Added
- MsspPartner model with white-label branding fields (logo_url, primary_color), plan tier, and max_customer_orgs limit
- MsspCustomerOrg model with tier (standard/premium/enterprise), free-form tags, notes, and onboarded_at timestamp
- MsspAlertRule model with five condition types: readiness_below, rto_breach, test_failure, no_test_in_days, threat_detected
- Alert rule scoping: all orgs, tier-specific (tier:premium), or tag-specific (tag:critical)
- Cross-org summary endpoint aggregating healthy/warning/critical counts, avg readiness score, total workloads/threats/incidents
- Per-customer scorecard endpoint with 6-month readiness trend and top risk workloads
- MSSP console portal page with 5-col KPI row, customer table with score/tier/threat badges, and alert rule toggles
- Migration 0017 adding mssp_partners, mssp_customer_orgs, mssp_alert_rules tables with cascade deletes

---

## [Unreleased] - Phase 15: Appliance Fleet Management

### Added
- ApplianceGroup model for organizing appliances by site or region with config template and tags
- ApplianceGroupMember join table with cascade deletes for clean group/appliance removal
- ApplianceHealthSnapshot model capturing CPU, memory, disk, Veeam/vCenter/Temporal connection state, version, and per-appliance alert list
- BulkConfigJob model for async config push to multiple appliances with per-appliance result tracking
- Fleet overview endpoint aggregating healthy/warning/offline counts and per-appliance status in one response
- Site group CRUD API with config_template for bulk configuration propagation
- Bulk config push endpoint: accepts appliance IDs and config dict, creates async job, returns job ID for status polling
- Fleet portal page with KPI cards, appliance rows showing status-colored borders with resource and connection badges, groups section, and bulk config JSON editor
- Migration 0016 adding appliance_groups, appliance_group_members, appliance_health_snapshots, and bulk_config_jobs tables

---

## [Unreleased] - Phase 13: Self-Service Onboarding Wizard

### Added
- OnboardingSession model with org-scoped unique constraint, step progress tracking, step_data JSONB for per-step completion evidence, and completed/dismissed flags
- Six-step onboarding flow: org_profile, deploy_appliance, connect_veeam, discover_workloads, first_test, complete
- Step completion predicates: each step has a typed check on step_data (appliance_id, veeam_connected, workload_count, first_test_run_id)
- Auto-complete trigger: session marks complete when step 6 is reached and overall progress is >= 80%
- Onboarding API: GET status (auto-creates session on first call), POST step advancement, POST dismiss, POST reset
- Full-screen wizard portal page with horizontal step stepper, org profile form, Docker deployment instructions, and step progress tracking
- Registration token display and 24-hour expiry hint on deploy_appliance step
- Security note confirming SOPS + age credential isolation in the wizard UI
- Migration 0014 adding onboarding_sessions table with org_id unique index

---

## [Unreleased] - Phase 12: DR Runbook Automation

### Added
- Runbook model with scenario classification (ransomware, datacenter_failure, cloud_outage, site_failover, custom) and RTO target
- RunbookStep model with seq ordering, depends_on_seq dependency graph, parallel flag, step_type, timeout, and on_failure policy (stop/continue/rollback)
- Six step types: recover_workload, health_check, notify, wait, manual_gate, run_script
- Topological sort engine resolving step dependencies into execution waves with concurrent parallel steps
- RunbookExecution and RunbookExecutionStep models tracking live step status, duration, output, and errors
- Temporal RunbookWorkflow: fetches plan, executes each step via typed activities, posts status after every step, finalizes with actual RTO and pass/fail
- Actual vs target RTO computation and rto_met flag stored per execution
- API at /v1/runbooks: list, create, get with execution plan, trigger execution, execution history, live step status
- Portal runbooks page: scenario filter pills, runbook cards with wave/step summary, RTO badge, execution history table
- Runbook execution detail view: wave timeline with per-step status, duration, output panel
- Migration 0013 adding runbooks, runbook_steps, runbook_executions, runbook_execution_steps tables

---

## [Unreleased] - Phase 11: AI Insights

### Added
- RTO trend prediction via linear regression: slope, projected next RTO, risk level (critical/high/medium/low), and estimated tests until breach
- Anomaly detection over RTO time series using z-score analysis (|z| > 2.0 flagged as spike or drop)
- Workload risk ranking scored across test recency, RTO proximity to target, and recent failure rate
- Rule-based natural language query handler covering workload counts, RTO breaches, threat status, readiness score, and provider performance
- Insights portal page with NL query bar, example query chips, risk ranking table
- API endpoints: GET /v1/insights/rto-prediction/{id}, GET /v1/insights/risk-ranking, POST /v1/insights/query

---

## [Unreleased] - Phase 10: Integrations Marketplace

### Added
- ServiceNow integration: creates incident via Table API with urgency/impact severity mapping
- Jira integration: creates issue via Jira Cloud REST v3 with Atlassian Document Format body and r3vp label
- PagerDuty integration: triggers alert via Events API v2 with critical/warning/info severity mapping
- Splunk integration: pushes events via HTTP Event Collector (HEC) with configurable index
- IBM QRadar integration: sends CEF syslog over UDP for recovery events and threat detections
- Microsoft Sentinel integration: posts to Log Analytics Data Collector API with HMAC-SHA256 SharedKey auth
- Integration catalog endpoint listing all six connectors with category and description
- Integration event log: every dispatch attempt stored with status, error detail, and response time
- CRUD API at /v1/integrations with test endpoint (POST /{id}/test) and enable/disable toggle
- Alembic migration 0012 adding integrations and integration_event_logs tables
- Integrations portal page: catalog card grid, active integrations table, event log

---

## [Unreleased] - Phase 9: Executive Reporting and CISO Scorecard

### Added
- Overall readiness score (0-100) computed from coverage (40%), pass rate (35%), RTO compliance (15%), threat penalty (up to 10 pts deducted)
- CISO scorecard PDF: score hero, KPI row, 6-month trend table, provider breakdown, top risks ranked by severity
- ScorecardSnapshot model for persisting monthly snapshots with provider_breakdown and top_risks JSONB
- DigestSchedule model for weekly/monthly/quarterly email delivery with configurable sections
- Scorecard trend API returning last N monthly snapshots
- Digest schedule CRUD API at /v1/executive/digest-schedules
- Alembic migration 0011 adding digest_schedules and scorecard_snapshots tables
- Scorecard portal page with score hero, trend chart, provider breakdown, risk ranking

---

## [Unreleased] - Phase 8: Multi-tenancy and RBAC

### Added
- Granular RBAC with 24 named permissions and five built-in system roles: owner, admin, operator, auditor, viewer
- Role, OrgMember, OrgInvite, ApiKey, and SsoConfig models
- Alembic migration 0010 adding roles, org_members, org_invites, api_keys, and sso_configs tables with system role seed data
- Permission registry (apps/api/src/services/rbac.py) with require_permission() enforcement helper
- Team management API: invite by email with 7-day expiring token, list members, change role, deactivate member
- API key management: scoped service account keys, SHA-256 hash stored (raw value shown once), revocation
- SAML 2.0 SSO configuration: Okta, Azure AD, Google Workspace, Ping Identity, generic SAML; cert + attribute mapping stored per org
- Portal /dashboard/settings/team page: member table with role badges, pending invites, invite form
- Portal API keys page: active keys with prefix and scopes, create form with grouped scope checkboxes
- Portal SSO settings page: provider card selector, config form, SP metadata display

---

## [Unreleased] - Phase 7: Compliance, Reporting, Scheduled Delivery and Evidence Vault

### Added
- Compliance PDF reports for SOC 2 Type II, ISO/IEC 27001:2022, NIST CSF 2.0, and cyber insurance
- Framework control mapping: CC7.5/CC9.1/A1.3 (SOC 2), A.8.13/A.8.14/A.5.29/A.5.30 (ISO 27001), RC.RP-01/02/05 (NIST CSF)
- SHA-256 signed PDF reports with digest stored in compliance_reports table and returned in X-SHA256 header
- ComplianceReport model and Alembic migration 0008
- Hash-chained audit trail in appliance (apps/appliance/src/audit/chain.py) using SHA-256 chain over SQLite
- Audit chain verify endpoint to confirm tamper-evidence on demand
- Report history endpoint listing all generated reports per org with summary metrics
- Jinja2 HTML template for compliance PDF rendering via weasyprint
- Portal /dashboard/reports page: framework selector, date range picker, generate button, history table, audit trail preview
- Scheduled report delivery: ReportSchedule model with cron expression, framework, period, recipients, enabled toggle
- Alembic migration 0009 adding report_schedules and evidence_bundles tables
- Report schedule CRUD API: GET/POST /v1/report-schedules, PATCH toggle, DELETE
- Temporal cron workflow (ReportScheduleWorkflow) fetches schedule config, generates PDF, delivers to all recipients
- Delivery service supporting email (SMTP), Slack incoming webhooks, and Teams adaptive card webhooks
- Evidence vault service: builds signed ZIP bundles containing manifest.json, compliance PDF, audit_chain.json, and per-workload artifacts (summary, steps, health checks)
- Evidence bundle API: POST /v1/reports/evidence-bundle returning ZIP with X-SHA256 and X-File-Count headers
- Portal /dashboard/reports/schedule page: schedule list, toggle active/paused, new schedule form with cadence selector
- Portal evidence vault view with bundle history, structure reference, and generate form

---

## [Unreleased] - Phase 6: Extended Hypervisors and Google Cloud

### Added
- Proxmox VE connector: proxmoxer REST API, PBS backup integration, snapshot create/restore
- Nutanix AHV connector: Prism Central v3 REST API, recovery point management
- RHV / oVirt connector: oVirt Engine Python SDK, snapshot preview and commit
- XenServer / Citrix Hypervisor connector: XenAPI XML-RPC, VM clone from snapshot
- Sangfor HCI connector: vendor REST API, token auth, snapshot restore
- GCP Backup connector: google-cloud-compute, Application Default Credentials, instance restore from snapshot
- Provider routing in Temporal activities extended from 4 to 10 providers
- Workload model: provider_cluster field for cluster/pool/zone metadata
- Alembic migration 0007 for provider_cluster column
- Portal /dashboard/providers: 10-provider card grid, extended hypervisor support matrix
- Portal dashboard: 10-provider coverage widget
- R3VP_PROVIDER env var now accepts: vmware, hyperv, azure, aws, proxmox, nutanix, rhv, xenserver, sangfor, gcp
- New pyproject.toml dependencies: proxmoxer>=2.0, google-cloud-compute>=1.14, google-auth>=2.28

---

## [0.5.0] - Phase 5 - 2026-06-17

### Added
- Veeam B&R 13.0.2 support: API version v1.2 with auto-detection via serverInfo
- Veeam 13 backup repositories endpoint: list repos with capacity and free space
- Veeam 13 malware detection events: ingest Veeam inline scanner findings
- Veeam 13 instant recovery path update: /instantRecovery/vm (v1.2) vs /instantRecovery/vmware/vm (v1.1)
- Veeam backup job control: trigger immediate backup jobs, monitor session progress
- Hyper-V connector: WMI-based VM inventory, checkpoint management, isolated virtual switch
- AWS Backup connector: vault inventory, EC2 recovery points, test restore to isolated VPC subnet, EC2 health checks
- Azure Backup connector: Recovery Services Vault integration, protected VM list, restore to isolated resource group
- Multi-cloud workflow routing: Temporal activities dispatch to correct connector based on configured provider
- Provider breakdown dashboard: per-provider workload count, pass rate, avg RTO
- /dashboard/providers page: detailed provider coverage cards with pass rate bar charts
- Provider filter on workload list
- Workload model: provider, cloud_resource_id, cloud_region fields
- Alembic migration 0006: workload provider columns
- Multi-cloud readiness API: GET /v1/multicloud/provider-summary, GET /v1/multicloud/workloads
- New dependencies: boto3, azure-identity, azure-mgmt-recoveryservicesbackup, msal

---

## [0.4.0] - Phase 4 - 2026-06-16

### Added
- Ransomware, malware, APT, and vulnerability signature database with automatic cloud sync
- File system and process scanner that cross-references running processes against the threat DB
- YARA rules engine: load and execute custom or community YARA rules against scanned artifacts
- SOAR integration: Splunk SOAR and Palo Alto XSOAR webhook triggers on threat detection
- SIEM integration: CEF/Syslog output for Splunk, IBM QRadar, and Microsoft Sentinel
- Automated incident response API: triggers an immediate Veeam backup and creates a SecOps workflow on threat detection
- VeeamONE reporting integration: pushes threat and recovery events to VeeamONE dashboards
- Threat scanner portal pages: scan dashboard, findings detail, active incidents
- Console notification pane: real-time threat alerts shown in portal without page refresh
- Email notifications for incident alerts (SES)

---

## [0.3.0] - Phase 3 - 2026-06-15

### Added
- SLA breach notifications: email (SES), Slack incoming webhook, Teams adaptive card webhook
- Notification channel management: POST/GET/DELETE /v1/notifications, scoped by org
- Portal settings page: org info, notification channels, default RTO/RPO targets
- Audit log CSV export: GET /v1/audit-log/export with 90-day date range
- Appliances list and detail pages in portal: status badges (active/stale/offline based on heartbeat)
- Role-based access control: admin and viewer roles, write endpoints protected with AdminUser dependency
- User provisioning endpoint: POST /v1/users/provision for role assignment
- Production Terraform: ECS Fargate auto-scaling (1-4 tasks), ALB with TLS 1.3, CloudFront CDN
- Cyber insurance evidence report: NIST CSF Recover function mapping, PDF attestation document
- Integration test suite: real Postgres tests for inventory sync upsert and readiness score calculation
- Portal-facing appliances API: GET/DELETE /v1/portal/appliances with workload counts
- Appliance deregister capability

### Changed
- finalise_run() now dispatches breach notifications as a best-effort post-commit step
- trigger_test_run, set_targets, set_schedule now require admin role

---

## [0.2.0] - Phase 2 - 2026-06-14

### Added
- Temporal workflow trigger wired into the API: trigger_test_run enqueues RecoveryTestWorkflow
- Temporal lifespan in FastAPI: connects on startup, graceful shutdown on exit
- Full inventory sync: sync_inventory activity posts explicit field mapping to relay client
- Portal workload detail page: stats, RTO/RPO targets form, test run history, Run Test Now
- Live test run progress view: 5-second polling while status is running/pending, step timeline
- PDF evidence report: Jinja2 HTML template rendered via WeasyPrint, full step/health check data
- Scheduled test runs: schedule_cron field on workloads, APScheduler loads and fires cron jobs
- Veeam version auto-detection: reads /api/v1/serverInfo on startup, routes to correct API path
- On-premises install script (bash): Docker check, cert generation, secrets template
- Windows PowerShell install script: same flow for Windows environments
- Appliance OVA packaging: Packer HCL2 template, configure-from-ovf.sh reads vSphere OVF properties

### Changed
- Restore point list routes to correct API path for Veeam v1.0 vs v1.1
- Instant recovery raises NotImplementedError on Veeam 10 (no API support)

---

## [0.1.0] - Phase 1 - 2026-06-13

### Added
- Python 3.12 monorepo with uv workspace (apps/appliance, apps/api, apps/portal)
- Lightweight appliance: outbound-only mTLS relay client, SOPS+age credential vault
- Veeam B&R REST API connector: token auth, auto-refresh, list jobs/VMs/restore points, instant recovery
- VMware vCenter connector: pyVmomi, isolated VLAN provisioning, VMware Tools polling, screenshot
- Temporal workflow: RecoveryTestWorkflow with 10 activities and saga teardown pattern
- Health checks: Windows OS (WinRM), Linux OS (SSH + systemctl), Active Directory LDAP, SQL Server stubs
- FastAPI SaaS backend: appliance relay, workload inventory, test run management, readiness scoring
- Auth0 JWT authentication with JWKS RS256 verification and org_id claim extraction
- PostgreSQL 16 schema: orgs, appliances, workloads, test_runs, test_run_steps, health_check_results, audit_events
- Alembic migrations (0001 initial)
- Next.js 14 portal: Auth0 login, dashboard with readiness gauge, RTO/RPO chart, workload grid
- mTLS client certificate verification: thumbprint checked against DB on every appliance request
- GitHub Actions CI: lint, typecheck, unit tests, integration tests, Docker builds
- Terraform modules: RDS PostgreSQL 16, S3 evidence bucket with KMS encryption
- mTLS cert generation scripts (bash + PowerShell)
- Architecture Decision Records: appliance runtime, Temporal workflow engine

---

## Roadmap

### Phase 5 (planned): Multi-cloud and Hyper-V support
- Hyper-V connector: WMI-based VM inventory and Hyper-V checkpoint recovery
- Azure Blob Storage backup connector
- AWS Backup connector
- Multi-cloud workload dashboard with provider breakdown

### Phase 6 (planned): Compliance frameworks and advanced reporting
- SOC 2 Type II evidence package generator
- ISO 27001 Annex A mapping
- CIS Controls v8 mapping
- Executive summary email digest (weekly/monthly)
- API-first reporting: programmatic evidence export for GRC tools
