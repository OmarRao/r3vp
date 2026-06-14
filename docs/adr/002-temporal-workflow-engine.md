# ADR-002: Workflow Engine — Temporal

**Status:** Accepted
**Date:** 2026-06-14

## Context
Recovery test workflows span 20–40 minutes, involve multiple external systems, must retry individual steps independently, and require guaranteed cleanup (saga pattern). A simple task queue would lose state on crash.

## Decision
Temporal.io — self-hosted worker on the appliance, Temporal Cloud as the server.

## Rationale
- Durable execution: workflow state survives appliance restart mid-test
- Built-in saga compensation: `TeardownIsolatedEnv` always runs via `finally`
- Full event history doubles as an audit trail at the workflow level
- `temporalio` Python SDK is stable and well-documented
- Temporal Cloud eliminates the need to run a Temporal cluster in the SaaS layer

## Consequences
- Temporal Cloud subscription cost
- mTLS required between appliance worker and Temporal Cloud (already in place)
- Teams unfamiliar with Temporal need onboarding (event-sourced mental model)
