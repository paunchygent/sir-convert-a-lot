---
type: task
id: TASK-SIRCON-05-04-03
title: Rebuild ML CLI Entrypoints as Thin Domain-Centric Wrappers
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
- '[ ] `pdm run qwen-preprocess` (or equivalent) correctly invokes the new preprocessing
  facade.'
- '[ ] `pdm run qwen-train` (or equivalent) correctly invokes the new training orchestrator.'
- '[ ] CLI flags and help text remain consistent or are improved.'
retired_ids:
- task-169-rebuild-ml-cli-entrypoints-as-thin-domain-centric-wrappers
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

Replace the existing `run_taskXXX` scripts in `devops/` with clean,
domain-centric CLI wrappers under `cli/ml/`, removing task IDs from the
user-facing command interface.

### PR Scope

- Create `scripts/sir_convert_a_lot/cli/ml/qwen_preprocess.py` (wraps `ml/qwen/preprocessing/pipeline.py`)
- Create `scripts/sir_convert_a_lot/cli/ml/qwen_train.py` (wraps `ml/qwen/training/orchestrator.py`)
- Remove old `run_task103_qwen_preprocessing.py` and `run_task101_hemma_qwen_pilot.py`.
- Update `pyproject.toml` or any shell scripts (e.g., `run-local-pdm.sh`) to point to the new CLI scripts.

### Deliverables

- [ ] New CLI scripts in `scripts/sir_convert_a_lot/cli/ml/`.
- [ ] Old `run_taskXXX` scripts removed.

### Acceptance Criteria

- [ ] `pdm run qwen-preprocess` (or equivalent) correctly invokes the new preprocessing facade.
- [ ] `pdm run qwen-train` (or equivalent) correctly invokes the new training orchestrator.
- [ ] CLI flags and help text remain consistent or are improved.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
