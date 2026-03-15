---
id: task-185-backport-legacy-qwen-resume-compatibility-and-stale-bundle-override-for-task-101-checkpoint-recovery
title: Backport legacy Qwen resume compatibility and stale bundle override for Task 101 checkpoint recovery
type: task
status: active
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/tasks/task-182-add-standalone-eval-and-scheduled-train-stop-resume-control-for-task-101-qwen-training.md
  - docs/backlog/tasks/task-183-control-checkpoint-cadence-and-retention-for-scheduled-task-101-qwen-training.md
  - docs/backlog/tasks/task-184-remediate-task-101-qwen-schedule-pointer-truth-schedule-path-fail-closed-validation-and-retention-3-checkpoint-proof-coverage.md
labels:
  - qwen
  - hemma
  - checkpoint-recovery
---

Task 185 is the compatibility-and-recovery follow-up for the shipped Task 101
scheduled-control posture. It exists to recover the most advanced legacy
checkpoint-backed training run truthfully after control-plane hardening exposed
that pre-schedule launch metadata can no longer be resumed without explicit
compatibility handling.

## Objective

Restore truthful resume support for the Task 101 legacy checkpoint run at
optimizer step `1236` by:

- backfilling safe defaults when older launch metadata lacks current required
  settings fields
- allowing operators to override a stale bundle root at resume time
- failing closed when the effective replacement bundle is missing or malformed
- suppressing stale pre-resume status/report artifacts while a resumed launch is
  still warming up on the reused run root
- proving the behavior with regression tests before the Hemma retry

## PR Scope

- Backward-compatible launch metadata loading for legacy detached Qwen runs.
- Resume CLI support for overriding `pilot_bundle_root`.
- Fail-closed preflight validation of the effective bundle root before detached
  relaunch.
- Detached status inspection truthfulness for resumed running launches that
  reuse a prior run root.
- Focused test coverage for legacy launch recovery and stale-bundle rejection.
- Docs/status updates for the recovery slice.

## Deliverables

- [ ] Legacy detached launch metadata can be loaded even when
  `throughput_profile_label` is absent.
- [ ] `qwen-train resume` accepts `--pilot-bundle-root` and applies it to the
  resumed launch settings.
- [ ] Resume fails before launch when the effective bundle root is missing or
  incomplete.
- [ ] Resumed running launches do not surface stale pre-resume `status.json` or
  `report.json` payloads as if they described the current container.
- [ ] Regression tests cover both successful override-based recovery and
  fail-closed stale-bundle behavior.
- [ ] Hemma resume is retried against the `1236`-step checkpoint after local
  verification passes.

## Acceptance Criteria

- [ ] The `1236`-step legacy Task 101 checkpoint can be resumed without manual
  launch JSON editing.
- [ ] Operators receive a clear bundle-integrity or missing-path failure before
  any detached container launch if the bundle override is wrong.
- [ ] Detached status/report inspection does not contradict the active resumed
  container with pre-resume artifacts from the reused run root.
- [ ] The compatibility fallback does not change current canonical launch
  defaults for new runs.
- [ ] Focused Qwen training orchestration tests pass with the new compatibility
  coverage.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Hemma resume retried
- [ ] Docs updated
