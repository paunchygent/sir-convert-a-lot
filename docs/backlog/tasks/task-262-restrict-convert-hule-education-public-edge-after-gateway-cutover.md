---
id: task-262-restrict-convert-hule-education-public-edge-after-gateway-cutover
title: Restrict convert.hule.education public edge after gateway cutover
type: task
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-33-sir-convert-gateway-fronted-public-access-and-internal-lane-migration.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md
labels:
  - public-edge
  - nginx
  - gateway
  - security
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Restrict the direct `convert.hule.education` public edge to the fail-closed
reserved/default posture after Gateway and internal/operator replacement lanes
are proven.

## PR Scope

- Enforce the ADR-0009 public-host posture: reserved fail-closed/default
  response.
- Remove or block direct public job APIs.
- Remove public docs/OpenAPI/metrics/detailed readiness exposure.
- Keep nginx-proxy default-host behavior fail-closed.
- Capture public-edge proof artifacts.

## Deliverables

- [ ] Updated compose/proxy/public-edge configuration.
- [ ] Public deny proof for job APIs and metadata endpoints.
- [ ] Unknown-host/default-host proof.
- [ ] Runbook update.

## Acceptance Criteria

- [ ] Public anonymous traffic cannot create, read, or download jobs/artifacts.
- [ ] `convert.hule.education` returns the ADR-0009 fail-closed/reserved
  posture. Any status page or external M2M API is blocked unless a separate
  accepted ADR exists.
- [ ] Product/browser access continues through Gateway.
- [ ] Internal and local operator lanes are unaffected.
- [ ] Linked HuleEdu/Skriptoteket route implementation and consumer migration
  signoffs exist before this task changes the public host.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
