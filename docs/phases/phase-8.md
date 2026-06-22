# Phase 8: Multi-tenancy and RBAC

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 8 adds enterprise-grade access control, team management, API keys, and SAML 2.0 SSO to R3VP. Every action in the platform is now gated by a named permission. Organizations can invite external auditors with read-only access, create service account keys scoped to specific operations, and federate login through their corporate IdP.

Five things ship in this phase:

1. **Granular RBAC** with five system roles and per-permission enforcement on every endpoint
2. **Team management** with invite-based onboarding and role assignment
3. **API keys** for CI/CD pipelines, GRC integrations, and SIEM connectors
4. **SAML 2.0 SSO** for Okta, Azure AD, Google Workspace, Ping Identity, and generic IdPs
5. **Migration 0010** adding roles, org_members, org_invites, api_keys, and sso_configs tables

---

## Role Definitions

Five built-in system roles cover every enterprise access pattern:

| Role | Description | Key Capabilities |
|---|---|---|
| owner | Full access including SSO | All permissions including sso:manage |
| admin | Full access except SSO | All permissions except sso:manage |
| operator | Day-to-day operations | Workloads, test runs, appliances, incidents |
| auditor | Compliance and evidence access | Read reports, generate PDFs, view audit log |
| viewer | Read-only across all views | View workloads, tests, reports, threats |

Roles cannot be modified or deleted. Org owners can create custom roles with any subset of the 24 available permissions.

---

## Permission Matrix

| Permission | Owner | Admin | Operator | Auditor | Viewer |
|---|---|---|---|---|---|
| workloads:read | Yes | Yes | Yes | Yes | Yes |
| workloads:write | Yes | Yes | Yes | | |
| workloads:delete | Yes | Yes | | | |
| test_runs:read | Yes | Yes | Yes | Yes | Yes |
| test_runs:trigger | Yes | Yes | Yes | | |
| reports:read | Yes | Yes | Yes | Yes | Yes |
| reports:generate | Yes | Yes | | Yes | |
| reports:schedule | Yes | Yes | | | |
| evidence:read | Yes | Yes | Yes | Yes | |
| threats:read | Yes | Yes | Yes | Yes | Yes |
| incidents:read | Yes | Yes | Yes | Yes | Yes |
| incidents:write | Yes | Yes | Yes | | |
| audit:read | Yes | Yes | Yes | Yes | |
| team:read | Yes | Yes | Yes | Yes | Yes |
| team:invite | Yes | Yes | | | |
| team:manage | Yes | Yes | | | |
| api_keys:read | Yes | Yes | | | |
| api_keys:write | Yes | Yes | | | |
| appliances:read | Yes | Yes | Yes | | |
| appliances:manage | Yes | Yes | Yes | | |
| settings:read | Yes | Yes | Yes | | |
| settings:write | Yes | Yes | | | |
| sso:manage | Yes | | | | |

---

## Team Management

### Invite flow

1. Admin or owner sends an invite by email and selects a role
2. A 7-day expiring token is generated and emailed to the recipient
3. Recipient clicks the link, authenticates via Auth0 or SSO, and is added as an OrgMember
4. All team actions are scoped to the org_id from the JWT claim

### API endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/team/members` | team:read | List active members |
| POST | `/api/v1/team/invites` | team:invite | Send invite by email |
| GET | `/api/v1/team/invites` | team:read | List pending invites |
| PATCH | `/api/v1/team/members/{id}/role` | team:manage | Change a member's role |
| DELETE | `/api/v1/team/members/{id}` | team:manage | Deactivate a member |

---

## API Keys

API keys give CI/CD pipelines, GRC tools, and SIEM connectors programmatic access without sharing user credentials.

### Key format

```
r3vp_<40 random URL-safe chars>
```

The full key is shown once at creation. Only the first 12 characters (prefix) and a SHA-256 hash are stored. The prefix is displayed in the UI for identification. Revocation is immediate.

### Scope-limited keys

Each key is issued with an explicit list of permission scopes. A key issued with `reports:read, evidence:read` cannot trigger test runs or access team management, even if the creator has those permissions.

### API endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/api-keys` | api_keys:read | List active keys (no raw values) |
| POST | `/api/v1/api-keys` | api_keys:write | Create key (returns raw value once) |
| DELETE | `/api/v1/api-keys/{id}` | api_keys:write | Revoke key immediately |

---

## SAML 2.0 SSO

### Supported identity providers

- Okta
- Microsoft Entra ID (Azure AD)
- Google Workspace
- Ping Identity
- Any generic SAML 2.0 compliant IdP

### Configuration

SSO is configured per org by the owner role only (`sso:manage` permission). Required fields:

| Field | Description |
|---|---|
| Entity ID | IdP-issued issuer URI |
| SSO URL | IdP SAML endpoint for authentication requests |
| Certificate | PEM-encoded IdP signing certificate |
| Attribute mapping | JSON mapping IdP attributes to R3VP fields (email, role) |

### Service provider metadata

R3VP exposes standard SP metadata at `/saml/metadata`. Give the ACS URL and SP Entity ID to your IdP:

```
SP Entity ID:    https://app.r3vp.io/saml/metadata
ACS URL:         https://app.r3vp.io/saml/acs
SLO URL:         https://app.r3vp.io/saml/slo
Name ID Format:  urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress
```

### API endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/sso` | sso:manage | Get current SSO config |
| PUT | `/api/v1/sso` | sso:manage | Create or update SSO config |
| PATCH | `/api/v1/sso/toggle` | sso:manage | Enable or disable SSO |

---

## Database Migration 0010

```sql
CREATE TABLE roles (
    id          UUID PRIMARY KEY,
    org_id      UUID,             -- NULL for built-in system roles
    name        VARCHAR(50) NOT NULL,
    description VARCHAR(255) DEFAULT '',
    permissions JSONB DEFAULT '[]',
    is_system   BOOLEAN DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (org_id, name)
);

CREATE TABLE org_members (
    id          UUID PRIMARY KEY,
    org_id      UUID NOT NULL,
    user_id     UUID REFERENCES users(id) NOT NULL,
    role_id     UUID REFERENCES roles(id) NOT NULL,
    invited_by  UUID REFERENCES users(id),
    joined_at   TIMESTAMPTZ DEFAULT now(),
    is_active   BOOLEAN DEFAULT true,
    UNIQUE (org_id, user_id)
);

CREATE TABLE org_invites (
    id          UUID PRIMARY KEY,
    org_id      UUID NOT NULL,
    email       VARCHAR(255) NOT NULL,
    role_id     UUID REFERENCES roles(id) NOT NULL,
    token       VARCHAR(64) UNIQUE NOT NULL,
    invited_by  UUID REFERENCES users(id) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE api_keys (
    id           UUID PRIMARY KEY,
    org_id       UUID NOT NULL,
    name         VARCHAR(200) NOT NULL,
    key_prefix   VARCHAR(12) NOT NULL,
    key_hash     VARCHAR(64) NOT NULL,
    scopes       JSONB DEFAULT '[]',
    last_used_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ,
    created_by   UUID REFERENCES users(id) NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    revoked      BOOLEAN DEFAULT false
);

CREATE TABLE sso_configs (
    id                UUID PRIMARY KEY,
    org_id            UUID UNIQUE NOT NULL,
    provider          VARCHAR(50) NOT NULL,
    entity_id         VARCHAR(512) NOT NULL,
    sso_url           VARCHAR(512) NOT NULL,
    certificate       VARCHAR(8192) NOT NULL,
    attribute_mapping JSONB DEFAULT '{}',
    enabled           BOOLEAN DEFAULT true,
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now()
);
```

Migration also seeds the five built-in system roles (owner, admin, operator, auditor, viewer) with `org_id = NULL` and `is_system = true`.

---

## Files Added

| File | Description |
|---|---|
| `apps/api/src/models/rbac.py` | Role, OrgMember, OrgInvite, ApiKey, SsoConfig models |
| `apps/api/src/services/rbac.py` | Permission registry and require_permission() helper |
| `apps/api/src/routers/team.py` | Member and invite management |
| `apps/api/src/routers/api_keys.py` | API key create, list, revoke |
| `apps/api/src/routers/sso.py` | SAML SSO configuration |
| `apps/api/src/db/migrations/versions/0010_rbac_teams_api_keys_sso.py` | Migration |
| `apps/portal/app/dashboard/settings/team/page.tsx` | Team management portal page |
| `docs/screenshots/mockup-team.html` | Team management mockup |
| `docs/screenshots/mockup-api-keys.html` | API keys mockup |
| `docs/screenshots/mockup-sso.html` | SSO configuration mockup |

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
