---
type: task
id: TASK-SIRCON-05-04-01
title: Migrate Qwen Preprocessing Logic to Domain-Centric Modules
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
- '- [ ] All preprocessing logic is located under `ml/qwen/preprocessing/`.'
- '- [ ] Preprocessing unit tests pass after import refactoring.'
- '- [ ] Logic remains behaviorally identical to the task-prefixed versions.'
retired_ids:
- task-167-migrate-qwen-preprocessing-logic-to-domain-centric-modules
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

Migrate all Qwen preprocessing logic from `devops/task103_*` to the new
`ml/qwen/preprocessing/` package, removing task-specific prefixes and
aligning with domain naming conventions.

### PR Scope

- Migrate `task103_qwen_preprocessing_core.py` → `ml/qwen/preprocessing/pipeline.py`
- Migrate `task103_qwen_preprocessing_asr.py` → `ml/qwen/preprocessing/asr.py`
- Migrate `task103_qwen_preprocessing_finalization.py` → `ml/qwen/preprocessing/finalization.py`
- Migrate `task103_qwen_preprocessing_storage.py` → `ml/qwen/preprocessing/storage.py`
- Move source adapters (`waxholm`, `fleurs`, `rixvox`) into `ml/qwen/preprocessing/sources/`.
- Migrate sharding and deduplication logic (Tasks 121, 137, etc.) to `ml/qwen/preprocessing/sharding.py`.
- Update all internal imports within the preprocessing domain.

### Deliverables

- [ ] `ml/qwen/preprocessing/` package fully populated.
- [ ] No `task103` or `task121` prefixes in the new preprocessing filenames.

### Acceptance Criteria

- [ ] All preprocessing logic is located under `ml/qwen/preprocessing/`.
- [ ] Preprocessing unit tests pass after import refactoring.
- [ ] Logic remains behaviorally identical to the task-prefixed versions.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
