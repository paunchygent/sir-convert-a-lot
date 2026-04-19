---
id: story-33-sir-convert-gateway-fronted-public-access-and-internal-lane-migration
title: Sir Convert gateway-fronted public access and internal lane migration
type: story
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/tasks/task-264-cut-over-huleedu-and-skriptoteket-sir-convert-consumers.md
  - docs/backlog/tasks/task-265-disable-direct-sir-convert-public-app-route-before-gateway-cutover.md
  - docs/backlog/tasks/task-262-restrict-convert-hule-education-public-edge-after-gateway-cutover.md
  - docs/backlog/tasks/task-263-run-sir-convert-gateway-cutover-proof-and-security-review.md
labels:
  - migration
  - gateway
  - cutover
  - public-edge
---

Implementation slice with acceptance-driven scope.

## Objective

Coordinate the migration from direct public Sir Convert access to the
Gateway-fronted product lane without breaking internal service consumers or
operator GPU-offload workflows.

## Scope

- Sequence consumer migration after inventory and ADR approval.
- Move browser/product callers to HuleEdu Gateway routes.
- Keep backend/internal workflows on a sanctioned internal lane where Gateway is
  not the right boundary.
- Require any user-originated backend-submitted workload to carry
  Gateway-issued `InternalIdentityContextV1` with audience `sir-convert-a-lot`
  through to Sir Convert.
- Restrict `convert.hule.education` only after proof that required consumers
  have a replacement lane.
- Keep direct public web access to Sir Convert disabled or fail-closed before
  the final live proof window.
- Re-enable the intended public edge as part of final live testing only after
  Gateway, internal, and operator replacement lanes are ready to prove.
- Preserve rollback and observability for the cutover window.

## Acceptance Criteria

- [ ] HuleEdu and Skriptoteket consumer cutover decisions are recorded.
- [ ] Direct public conversion routes are removed, blocked, or deliberately
  reduced after consumers move.
- [ ] Browser-derived backend jobs do not collapse to global service-key
  ownership.
- [ ] Internal and local operator lanes remain usable.
- [ ] Public-edge and default-host behavior remain fail-closed.
- [ ] Pre-final testing keeps the direct public Sir Convert web surface
  disabled or fail-closed.
- [ ] Final live testing deliberately re-enables the intended public edge and
  proves only approved Gateway/internal/operator lanes work.
- [ ] Final proof covers all target lanes.

## Test Requirements

- [ ] Public unauthenticated probes fail closed.
- [ ] Direct `convert.hule.education` web access is disabled or fail-closed
  before final live proof.
- [ ] Final live proof re-enables the intended public edge and verifies the
  ADR-0009 fail-closed/reserved posture for direct non-Gateway traffic.
- [ ] Gateway-authenticated conversion flow succeeds.
- [ ] Internal direct service-call proof succeeds.
- [ ] Local tunnel/offload proof succeeds.
- [ ] Unknown-host/default-host probe still returns reserved placeholder.

## Done Definition

Done when product traffic is Gateway-fronted, direct public exposure is
restricted, and the internal/operator lanes have durable proof.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
