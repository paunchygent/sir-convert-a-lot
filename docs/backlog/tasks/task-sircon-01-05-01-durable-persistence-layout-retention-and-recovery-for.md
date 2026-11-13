---
type: task
id: TASK-SIRCON-01-05-01
title: Durable persistence layout retention and recovery for containerized runtime
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
story: ST-SIRCON-01-05
task_kind: story
acceptance_criteria:
- '- [ ] Restarted containers recover job metadata/result discoverability per contract.'
- '- [ ] Retention sweeper behavior remains deterministic and profile-scoped.'
- '- [ ] No prod/eval data-root collision is possible under documented configuration.'
- '- [ ] Validation evidence includes restart/recovery and retention edge cases.'
retired_ids:
- task-23-durable-persistence-layout-retention-and-recovery-for-containerized-runtime
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

Define and enforce durable container data layout and lifecycle semantics so restart/redeploy
operations preserve required job state/artifacts while retention policies remain deterministic.

### PR Scope

- Define canonical persistent volume layout for prod/eval lanes.
- Enforce retention and sweeper behavior for containerized filesystem roots.
- Validate recovery behavior after container restart and process restarts.
- Ensure profile isolation prevents cross-lane data contamination.

Out of scope:

- compose/image packaging surfaces (Task 22),
- operator runbook/deployment playbook and Hemma end-to-end verification (Task 24).

### Deliverables

- [ ] Durable data-root layout contract for containerized prod/eval runtime.
- [ ] Retention/recovery behavior implementation updates where required.
- [ ] Regression/integration tests for restart recovery and retention sweeper behavior.
- [ ] Documentation updates for persistence guarantees and failure/recovery boundaries.

### Acceptance Criteria

- [ ] Restarted containers recover job metadata/result discoverability per contract.
- [ ] Retention sweeper behavior remains deterministic and profile-scoped.
- [ ] No prod/eval data-root collision is possible under documented configuration.
- [ ] Validation evidence includes restart/recovery and retention edge cases.

### Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
