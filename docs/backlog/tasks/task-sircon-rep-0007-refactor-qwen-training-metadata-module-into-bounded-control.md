---
type: task
id: TASK-SIRCON-REP-0007
title: Refactor Qwen training metadata module into bounded control-plane modules without
  compatibility shims
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- "[ ] No behavior change in launch/resume/eval/diagnose/schedule/status/stop\n  command\
  \ outcomes."
- "[ ] No legacy shim, alias module, pass-through wrapper, or compatibility\n  bridge\
  \ remains for the old `metadata.py` surface."
- "[ ] All touched hot-path modules remain under the Story 28 / RULE-095 line\n  caps."
- "[ ] Existing artifact shape contracts (`launch.json`, `status.json`,\n  `status.md`,\
  \ `stop.json`, `latest-launch.json`, `latest_checkpoint.json`)\n  are preserved."
- "[ ] Validation gates pass:\n  - `pdm run format-all`\n  - `pdm run lint-fix`\n\
  \  - `pdm run typecheck-all`\n  - focused pytest for Qwen training control-plane/reporting\
  \ metadata\n  - `pdm run validate-tasks`\n  - `pdm run validate-docs`"
retired_ids:
- task-200-refactor-qwen-training-metadata-module-into-bounded-control-plane-modules-without-compatibility-shims
---

## Context

## Impact And Escalation

## Decision And Assumption Ledger

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Readiness

## Closeout

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Refactor `scripts/sir_convert_a_lot/ml/qwen/training/metadata.py` into
bounded SRP modules under the Qwen Story 28 architecture owners while
preserving runtime behavior, JSON/Markdown artifact contracts, and CLI
operator workflows.

This task is explicitly contract-preserving and must not alter training,
schedule, resume, diagnose, eval, or status semantics.

### PR Scope

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

### Deliverables

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

### Acceptance Criteria

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

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
