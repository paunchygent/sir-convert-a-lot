---
id: task-264-cut-over-huleedu-and-skriptoteket-sir-convert-consumers
title: Cut over HuleEdu and Skriptoteket Sir Convert consumers
type: task
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-33-sir-convert-gateway-fronted-public-access-and-internal-lane-migration.md
  - docs/backlog/stories/story-37-huleedu-gateway-proxy-integration-for-sir-convert-workloads.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
labels:
  - huledu
  - skriptoteket
  - migration
  - gateway
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Cut over HuleEdu and Skriptoteket Sir Convert consumers to the target lane
recorded in the inventory: Gateway for browser/product traffic and sanctioned
direct internal access for backend workflows.

## PR Scope

- Use Task 256 inventory as the migration source of truth.
- Update HuleEdu and Skriptoteket callers or create cross-repo tasks where the
  implementation lives outside this repo.
- Preserve Gateway-issued `InternalIdentityContextV1` user context for any
  user-originated backend-submitted conversion job.
- Rotate or retire old direct public API-key usage after callers move.
- Preserve direct internal and operator workflows.
- Update docs and verification scripts to stop encouraging stale public direct
  use.

## Deliverables

- [ ] HuleEdu caller migration evidence.
- [ ] Skriptoteket caller migration evidence.
- [ ] Route contract tests, consumer smoke evidence, and cross-repo signoff
  references.
- [ ] Updated downstream docs.
- [ ] Secret/credential cleanup or rotation plan.

## Acceptance Criteria

- [ ] No known browser/product caller depends on direct public
  `convert.hule.education` job routes.
- [ ] Backend/internal direct callers are still supported through the internal
  identity contract.
- [ ] User-originated workloads retain context-derived ownership through job
  creation, status, result, and artifact reads.
- [ ] Existing user-facing conversion use cases continue to work.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
