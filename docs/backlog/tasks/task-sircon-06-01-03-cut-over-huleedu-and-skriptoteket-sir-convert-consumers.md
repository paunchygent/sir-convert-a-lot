---
type: task
id: TASK-SIRCON-06-01-03
title: Cut over HuleEdu and Skriptoteket Sir Convert consumers
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-06-01
task_kind: story
acceptance_criteria:
- '- [ ] No known browser/product caller depends on direct public `convert.hule.education`
  job routes.'
- '- [ ] Backend/internal direct callers are still supported through the internal
  identity contract.'
- '- [ ] User-originated workloads retain context-derived ownership through job creation,
  status, result, and artifact reads.'
- '- [ ] Existing user-facing conversion use cases continue to work.'
retired_ids:
- task-264-cut-over-huleedu-and-skriptoteket-sir-convert-consumers
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Cut over HuleEdu and Skriptoteket Sir Convert consumers to the target lane
recorded in the inventory: Gateway for browser/product traffic and sanctioned
direct internal access for backend workflows.

### PR Scope

- Use Task 256 inventory as the migration source of truth.
- Update HuleEdu and Skriptoteket callers or create cross-repo tasks where the
  implementation lives outside this repo.
- Preserve Gateway-issued `InternalIdentityContextV1` user context for any
  user-originated backend-submitted conversion job.
- Rotate or retire old direct public API-key usage after callers move.
- Preserve direct internal and operator workflows.
- Update docs and verification scripts to stop encouraging stale public direct
  use.

### Deliverables

- [ ] HuleEdu caller migration evidence.
- [ ] Skriptoteket caller migration evidence.
- [ ] Route contract tests, consumer smoke evidence, and cross-repo signoff
  references.
- [ ] Updated downstream docs.
- [ ] Secret/credential cleanup or rotation plan.

### Acceptance Criteria

- [ ] No known browser/product caller depends on direct public
  `convert.hule.education` job routes.
- [ ] Backend/internal direct callers are still supported through the internal
  identity contract.
- [ ] User-originated workloads retain context-derived ownership through job
  creation, status, result, and artifact reads.
- [ ] Existing user-facing conversion use cases continue to work.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
