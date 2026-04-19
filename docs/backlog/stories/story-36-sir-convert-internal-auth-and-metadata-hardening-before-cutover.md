---
id: story-36-sir-convert-internal-auth-and-metadata-hardening-before-cutover
title: Sir Convert internal auth and metadata hardening before cutover
type: story
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/tasks/task-258-fix-unauthenticated-sir-convert-api-failures-and-prod-metadata-exposure.md
  - docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md
labels:
  - auth
  - hardening
  - metadata
  - internal-service
---

Implementation slice with acceptance-driven scope.

## Objective

Make Sir Convert safe to keep running during and after the Gateway cutover by
fixing unauthenticated failure behavior, reducing production metadata exposure,
and defining internal caller identity.

## Scope

- Return deterministic `401` or `403` responses for missing/invalid credentials.
- Prevent stale durable job data from turning unauthorized requests into `500`
  responses.
- Disable or gate public docs/OpenAPI/metrics/detailed readiness in production.
- Add security headers at app or proxy layer.
- Define and implement Sir Convert's internal identity verification contract.
- Persist context-derived job ownership and enforce it on status, result,
  artifact, partial, checkpoint, resume, cancel, template, SSE, and webhook
  access.

## Acceptance Criteria

- [ ] Missing or invalid auth never returns `500`.
- [ ] Public docs/OpenAPI/metrics are disabled or gated in production.
- [ ] Detailed readiness metadata is internal-only or intentionally reduced.
- [ ] Sir Convert rejects unsigned public user identity headers.
- [ ] `InternalIdentityContextV1` verification and Sir Convert route
  authorization are tested.
- [ ] The existing service API key is treated as transport only, not as global
  job/artifact ownership.

## Test Requirements

- [ ] Focused HTTP auth/error tests.
- [ ] Production-profile app tests for docs/OpenAPI/metrics exposure.
- [ ] Live or local public-edge probes proving unauthenticated deny behavior.
- [ ] `pdm run docs-validate`

## Done Definition

Done when Sir Convert can remain available internally while external
unauthorized traffic fails cleanly and reveals no unnecessary metadata.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
