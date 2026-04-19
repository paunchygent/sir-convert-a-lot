---
id: story-35-preserve-internal-service-and-local-operator-sir-convert-lanes
title: Preserve internal service and local operator Sir Convert lanes
type: story
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md
  - docs/backlog/tasks/task-261-preserve-local-operator-tunnel-lane-for-gpu-backed-conversions.md
labels:
  - internal-service
  - operator-lane
  - tunnel
  - gpu
  - hemma
---

Implementation slice with acceptance-driven scope.

## Objective

Preserve Sir Convert as a direct internal Hemma network resource and local
operator GPU-offload service after product/browser access moves behind Gateway.

## Scope

- Document sanctioned internal service-to-service access.
- Require the Sir Convert `InternalIdentityContextV1` authorization profile
  for internal and operator job ownership, status reads, and artifact access.
- Preserve local tunnel/CLI workflows for heavy conversions.
- Keep GPU-first behavior and conversion API semantics stable.
- Separate operator/internal docs from public/product guidance.

## Acceptance Criteria

- [ ] Internal backend callers have a documented direct lane that does not
  require browser Gateway routing.
- [ ] Direct internal callers use the Sir Convert `InternalIdentityContextV1`
  authorization profile for job and artifact authorization.
- [ ] Local operator tunnel lane remains documented and tested.
- [ ] Operator credentials are explicit and never persisted in reports.
- [ ] GPU-backed conversion proof still works through the local lane.
- [ ] Docs no longer confuse direct local, internal, and public lanes.

## Test Requirements

- [ ] Internal network smoke proof.
- [ ] Local tunnel CLI proof.
- [ ] GPU/readiness proof through sanctioned wrappers.
- [ ] Docs validation.

## Done Definition

Done when internal and local operator workflows are preserved with durable
evidence and no public-access ambiguity.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
