---
id: 'task-169-rebuild-ml-cli-entrypoints-as-thin-domain-centric-wrappers'
title: 'Rebuild ML CLI Entrypoints as Thin Domain-Centric Wrappers'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-27-transition-to-domain-centric-ml-pipeline-structure.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
labels:
  - refactor
  - cli
  - qwen
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the existing `run_taskXXX` scripts in `devops/` with clean,
domain-centric CLI wrappers under `cli/ml/`, removing task IDs from the
user-facing command interface.

## PR Scope

- Create `scripts/sir_convert_a_lot/cli/ml/qwen_preprocess.py` (wraps `ml/qwen/preprocessing/pipeline.py`)
- Create `scripts/sir_convert_a_lot/cli/ml/qwen_train.py` (wraps `ml/qwen/training/orchestrator.py`)
- Remove old `run_task103_qwen_preprocessing.py` and `run_task101_hemma_qwen_pilot.py`.
- Update `pyproject.toml` or any shell scripts (e.g., `run-local-pdm.sh`) to point to the new CLI scripts.

## Deliverables

- [ ] New CLI scripts in `scripts/sir_convert_a_lot/cli/ml/`.
- [ ] Old `run_taskXXX` scripts removed.

## Acceptance Criteria

- [ ] `pdm run qwen-preprocess` (or equivalent) correctly invokes the new preprocessing facade.
- [ ] `pdm run qwen-train` (or equivalent) correctly invokes the new training orchestrator.
- [ ] CLI flags and help text remain consistent or are improved.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
