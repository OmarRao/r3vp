# Phase 23: Integration Config Validation

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

The integrations marketplace (ServiceNow, Jira, PagerDuty, Splunk, QRadar,
Sentinel) already had CRUD, a real dispatch path, a test action, and event
logging. The gap was that `create_integration` validated only the integration
type and trigger events, not the config contents, so a connector saved without
its required fields (e.g. a PagerDuty integration with no routing key, or a
Sentinel one with no workspace/shared key) would be accepted and only fail at
the first real event.

## Validation

`src/services/integrations/validation.py` adds `validate_integration_config`
(pure, unit-tested), checking per connector:

| Type | Required fields |
|---|---|
| servicenow | instance_url, api_token |
| jira | base_url, api_token, email, project_key |
| pagerduty | routing_key |
| splunk | hec_url, hec_token |
| qradar | syslog_host, syslog_port |
| sentinel | workspace_id, shared_key |

Plus: URL fields (instance_url, base_url, hec_url) must be http(s), and the
QRadar syslog port must be a valid 1-65535 port. `POST /v1/integrations` returns
a 400 listing every problem when the config is invalid.

## Fix

`create_integration` stored `created_by` as `None` because it read a nonexistent
`user.user_id`. It now resolves the local `users.id` via `resolve_local_user_id`,
consistent with the earlier reports and report-schedules fixes.

## Testing

- Unit tests (`tests/test_integration_validation.py`): valid configs, missing
  fields, non-URL rejection, QRadar port validation, unknown type, and the
  create 400 path.
- Integration test (`tests/integration/test_integration_create.py`, real
  Postgres): a valid config persists (201) and `created_by` resolves to the
  seeded user's id.
- 29 API unit tests pass; 6 integration tests pass against Postgres 16.

## Follow-up

The natural-language insights query (`/v1/insights/query`) remains the last
mock-backed endpoint in the analytics surface.

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
