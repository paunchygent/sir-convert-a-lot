---
id: task-257-publish-adr-0009-for-gateway-fronted-sir-convert-access
title: Publish ADR-0009 for Gateway-fronted Sir Convert access
type: task
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-34-adr-and-contract-authority-for-sir-convert-gateway-cutover.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
labels:
  - adr
  - gateway
  - auth
  - planning
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Finalize ADR-0009 as the accepted architecture decision for Gateway-fronted
public Sir Convert access and preserved internal/operator lanes.

## PR Scope

- Review and update the proposed ADR text after Task 256 inventory evidence.
- Keep ADR-0009 proposed until Task 259 locks Sir Convert's
  `InternalIdentityContextV1` authorization profile and the context-derived
  job/artifact authorization model.
- Record accepted access-lane matrix and migration stop conditions.
- Link ADR-0009 from converter docs, downstream integration docs, runbook, and
  active backlog items.
- Keep the ADR explicit about what moves to Gateway and what stays direct
  internal/operator.

## Deliverables

- [ ] Accepted ADR-0009.
- [ ] Completed Task 259 identity-contract prerequisite.
- [ ] Updated links from affected docs.
- [ ] Follow-up implementation tasks are confirmed or revised.

## Acceptance Criteria

- [ ] ADR explicitly preserves internal service direct access.
- [ ] ADR explicitly preserves local operator GPU-offload access.
- [ ] ADR explicitly rejects anonymous/direct public job API access as the
  normal product lane.
- [ ] ADR names HuleEdu `InternalIdentityContextV1` with audience
  `sir-convert-a-lot` as the first enforced identity model for
  Gateway/user-originated traffic.
- [ ] ADR keeps direct public host posture fail-closed/reserved unless a
  separate accepted ADR creates another public surface.
- [ ] Docs validation passes.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
