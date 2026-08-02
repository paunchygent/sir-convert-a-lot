---
type: task
id: TASK-SIRCON-05-04-02
title: Migrate Qwen Training and Detached Orchestration to Domain-Centric Modules
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
story: ST-SIRCON-05-04
task_kind: story
acceptance_criteria:
- '[ ] All training logic is located under `ml/qwen/training/`.'
- '[ ] Training unit tests pass after import refactoring.'
- '[ ] Training logic remains behaviorally identical to the task-prefixed version.'
retired_ids:
- task-168-migrate-qwen-training-and-detached-orchestration-to-domain-centric-modules
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

Migrate all Qwen training and orchestration logic from `devops/task101_*` to the
new `ml/qwen/training/` package, removing task-specific prefixes and
aligning with domain naming conventions.

### PR Scope

- Migrate `task101_qwen_pilot_runtime.py` → `ml/qwen/training/orchestrator.py`
- Migrate `task101_qwen_pilot_probe.py` → `ml/qwen/training/trainer.py`
- Migrate `task101_qwen_pilot_status_reporter.py` → `ml/qwen/training/reporting.py`
- Migrate `task101_qwen_pilot_resource_monitor.py` → `ml/qwen/training/monitoring.py`
- Migrate `task101_qwen_pilot_bundle.py` → `ml/qwen/training/bundles.py`
- Migrate `task101_qwen_pilot_metadata.py` → `ml/qwen/training/metadata.py`
- Update all internal imports within the training domain.

### Deliverables

- [ ] `ml/qwen/training/` package fully populated.
- [ ] No `task101` prefixes in the new training filenames.

### Acceptance Criteria

- [ ] All training logic is located under `ml/qwen/training/`.
- [ ] Training unit tests pass after import refactoring.
- [ ] Training logic remains behaviorally identical to the task-prefixed version.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
