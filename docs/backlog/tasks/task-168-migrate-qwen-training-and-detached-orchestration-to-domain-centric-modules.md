---
id: task-168-migrate-qwen-training-and-detached-orchestration-to-domain-centric-modules
title: Migrate Qwen Training and Detached Orchestration to Domain-Centric Modules
type: task
status: proposed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-27-transition-to-domain-centric-ml-pipeline-structure.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
labels:
  - refactor
  - training
  - qwen
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Migrate all Qwen training and orchestration logic from `devops/task101_*` to the
new `ml/qwen/training/` package, removing task-specific prefixes and
aligning with domain naming conventions.

## PR Scope

- Migrate `task101_qwen_pilot_runtime.py` → `ml/qwen/training/orchestrator.py`
- Migrate `task101_qwen_pilot_probe.py` → `ml/qwen/training/trainer.py`
- Migrate `task101_qwen_pilot_status_reporter.py` → `ml/qwen/training/reporting.py`
- Migrate `task101_qwen_pilot_resource_monitor.py` → `ml/qwen/training/monitoring.py`
- Migrate `task101_qwen_pilot_bundle.py` → `ml/qwen/training/bundles.py`
- Migrate `task101_qwen_pilot_metadata.py` → `ml/qwen/training/metadata.py`
- Update all internal imports within the training domain.

## Deliverables

- [ ] `ml/qwen/training/` package fully populated.
- [ ] No `task101` prefixes in the new training filenames.

## Acceptance Criteria

- [ ] All training logic is located under `ml/qwen/training/`.
- [ ] Training unit tests pass after import refactoring.
- [ ] Training logic remains behaviorally identical to the task-prefixed version.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
