---
id: task-200-refactor-qwen-training-metadata-module-into-bounded-control-plane-modules-without-compatibility-shims
title: Refactor Qwen training metadata module into bounded control-plane modules without compatibility shims
type: task
status: in_progress
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-155-refactor-qwen-checkpoint-and-task-101-pilot-god-files-into-srp-modules.md
  - docs/backlog/current.md
labels:
  - qwen
  - training
  - refactor
  - architecture
  - control-plane
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Refactor `scripts/sir_convert_a_lot/ml/qwen/training/metadata.py` into
bounded SRP modules under the Qwen Story 28 architecture owners while
preserving runtime behavior, JSON/Markdown artifact contracts, and CLI
operator workflows.

This task is explicitly contract-preserving and must not alter training,
schedule, resume, diagnose, eval, or status semantics.

## PR Scope

- Split the mixed concerns currently in `metadata.py` into bounded module
  owners:
  - launch/status/stop/latest/checkpoint path resolution
  - launch metadata deserialization + compatibility defaults
  - status markdown rendering
  - artifact writing primitives reused by control-plane and reporting flows
- Introduce explicit interface boundaries (ports) for metadata read/write and
  status markdown rendering so use cases depend on contracts rather than
  monolithic helpers.
- Wire concrete implementations through the control-plane composition root in a
  way that supports Dishka-based dependency injection during the import
  migration.
- Migrate imports in one pass across control-plane and schedule surfaces.
- Delete `metadata.py` after migration is complete.

## Deliverables

- [ ] New bounded control-plane metadata modules exist with Google module
  docstrings and clear ownership boundaries.
- [ ] A metadata port contract exists for loader/writer/renderer responsibilities.
- [ ] `control_plane` and `schedule_runner.py` imports are migrated to bounded
  modules without compatibility wrappers.
- [ ] Legacy `metadata.py` is removed after migration.
- [ ] Focused tests exist for:
  - launch metadata loading + compatibility defaults
  - latest-pointer and checkpoint-path resolution
  - status markdown rendering parity

## Acceptance Criteria

- [ ] No behavior change in launch/resume/eval/diagnose/schedule/status/stop
  command outcomes.
- [ ] No legacy shim, alias module, pass-through wrapper, or compatibility
  bridge remains for the old `metadata.py` surface.
- [ ] All touched hot-path modules remain under the Story 28 / RULE-095 line
  caps.
- [ ] Existing artifact shape contracts (`launch.json`, `status.json`,
  `status.md`, `stop.json`, `latest-launch.json`, `latest_checkpoint.json`)
  are preserved.
- [ ] Validation gates pass:
  - `pdm run format-all`
  - `pdm run lint-fix`
  - `pdm run typecheck-all`
  - focused pytest for Qwen training control-plane/reporting metadata
  - `pdm run validate-tasks`
  - `pdm run validate-docs`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
