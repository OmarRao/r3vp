# Phase 10: Integrations Marketplace

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 10 connects R3VP to the tools enterprise teams already use. Six integrations ship: two ITSM (ServiceNow, Jira), one alerting (PagerDuty), and three SIEM (Splunk, IBM QRadar, Microsoft Sentinel). Every integration can be scoped to specific trigger events and tested with a single click before going live.

---

## Integrations

| Integration | Category | Protocol | Trigger Method |
|---|---|---|---|
| ServiceNow | ITSM | REST (Table API) | Create incident record |
| Jira | ITSM | REST (Jira Cloud v3) | Create issue with label |
| PagerDuty | Alerting | Events API v2 | Trigger alert with severity |
| Splunk | SIEM | HTTP Event Collector (HEC) | Push JSON event |
| IBM QRadar | SIEM | CEF Syslog UDP/TCP | Send CEF log line |
| Microsoft Sentinel | SIEM | Log Analytics Data Collector API | Send to workspace |

---

## Trigger Events

Each integration subscribes to one or more events:

| Event | Description |
|---|---|
| sla_breach | A workload's actual RTO exceeded its target |
| test_failed | A recovery test completed with a failing status |
| threat_detected | Threat scanner found a new high or critical finding |
| incident_created | A new incident was opened in the incidents module |

---

## Integration Catalog

A read-only catalog endpoint (`GET /api/v1/integrations/catalog`) returns all available integrations with type, name, description, and category. The portal renders this as a card grid so operators can see what is available and connect with a single form.

---

## API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/integrations/catalog` | none | Available integrations catalog |
| GET | `/api/v1/integrations` | settings:read | List configured integrations |
| POST | `/api/v1/integrations` | settings:write | Create integration |
| POST | `/api/v1/integrations/{id}/test` | settings:write | Send test event |
| PATCH | `/api/v1/integrations/{id}/toggle` | settings:write | Enable or disable |
| DELETE | `/api/v1/integrations/{id}` | settings:write | Remove integration |
| GET | `/api/v1/integrations/{id}/logs` | settings:read | Last 50 event dispatch logs |

---

## Integration Config Shapes

### ServiceNow
```json
{
  "instance_url": "https://acmecorp.service-now.com",
  "api_token": "<bearer-token>",
  "caller_id": "r3vp"
}
```

### Jira
```json
{
  "base_url": "https://acmecorp.atlassian.net",
  "email": "r3vp-svc@acmecorp.com",
  "api_token": "<token>",
  "project_key": "DR"
}
```

### PagerDuty
```json
{
  "routing_key": "<Events API v2 integration key>"
}
```

### Splunk HEC
```json
{
  "hec_url": "https://splunk.acmecorp.com:8088",
  "hec_token": "<HEC token>",
  "index": "r3vp",
  "verify_ssl": true
}
```

### IBM QRadar (CEF Syslog)
```json
{
  "syslog_host": "qradar.acmecorp.com",
  "syslog_port": 514
}
```

### Microsoft Sentinel
```json
{
  "workspace_id": "<Log Analytics workspace ID>",
  "shared_key": "<primary or secondary key>",
  "log_type": "R3VP"
}
```

---

## Event Dispatch Log

Every dispatch attempt is logged in `integration_event_logs` with event type, status (ok/error), error detail if any, and response time in milliseconds. The last 50 entries per integration are accessible via the API and portal.

---

## Database Migration 0012

```sql
CREATE TABLE integrations (
    id                UUID PRIMARY KEY,
    org_id            UUID NOT NULL,
    integration_type  VARCHAR(50) NOT NULL,
    name              VARCHAR(200) NOT NULL,
    config            JSONB DEFAULT '{}',
    trigger_events    JSONB DEFAULT '[]',
    enabled           BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    last_status       VARCHAR(20),
    created_at        TIMESTAMPTZ DEFAULT now(),
    created_by        UUID REFERENCES users(id)
);

CREATE TABLE integration_event_logs (
    id              UUID PRIMARY KEY,
    integration_id  UUID REFERENCES integrations(id) NOT NULL,
    org_id          UUID NOT NULL,
    event_type      VARCHAR(50) NOT NULL,
    payload         JSONB DEFAULT '{}',
    status          VARCHAR(20) NOT NULL,
    error_detail    VARCHAR(1000),
    triggered_at    TIMESTAMPTZ DEFAULT now(),
    response_ms     INTEGER
);
```

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
