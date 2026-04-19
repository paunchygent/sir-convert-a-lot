---
id: story-34-adr-and-contract-authority-for-sir-convert-gateway-cutover
title: ADR and contract authority for Sir Convert gateway cutover
type: story
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
  - docs/backlog/tasks/task-256-inventory-sir-convert-callers-and-access-lanes-before-gateway-cutover.md
  - docs/backlog/tasks/task-257-publish-adr-0009-for-gateway-fronted-sir-convert-access.md
labels:
  - adr
  - gateway
  - auth
  - contracts
---

Implementation slice with acceptance-driven scope.

## Objective

Establish the normative decision and contract authority for moving Sir
Convert-a-Lot public/product access behind HuleEdu Gateway while retaining
internal service and local operator lanes.

## Scope

- Publish and review ADR-0009.
- Keep the caller/access-lane inventory reference as decision input.
- Treat Task 259 as a hard prerequisite for ADR acceptance so the Sir-specific
  `InternalIdentityContextV1` authorization profile is not deferred.
- Update converter, downstream integration, internal adapter, and runbook
  surfaces after the ADR is accepted.
- Record cross-repo HuleEdu/Skriptoteket implementation handoff boundaries.

## Acceptance Criteria

- [ ] ADR-0009 is accepted or explicitly revised with unresolved questions
  tracked.
- [ ] The inventory reference contains enough caller/lane data to support
  migration sequencing.
- [ ] The Sir Convert `InternalIdentityContextV1` authorization profile is
  locked or the ADR remains proposed.
- [ ] Converter and downstream docs distinguish public Gateway, internal
  direct, and local operator lanes.
- [ ] The ADR names stop conditions for breaking existing internal and local
  offload use cases.

## Test Requirements

- [ ] `pdm run docs-validate`
- [ ] `pdm run handoff-validate`
- [ ] `git diff --check`

## Done Definition

Done when the ADR and migration reference are accepted as the governing
authority for implementation tasks.

## Checklist

- [ ] ADR and docs authority complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
