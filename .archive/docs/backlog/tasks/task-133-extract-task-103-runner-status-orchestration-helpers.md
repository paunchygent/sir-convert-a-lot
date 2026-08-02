---
id: task-133-extract-task-103-runner-status-orchestration-helpers
title: Extract Task 103 runner status orchestration helpers
type: task
status: completed
priority: high
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-132-decompose-task103-test-surface-by-domain.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-131-add-backward-compatible-resume-index-for-drive-backed-qwen-row-processing.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
labels:
  - qwen
  - preprocessing
  - modularity
  - orchestration
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Extract Task 103 run-status lifecycle and heartbeat orchestration out of the
public runner entrypoint so `run_task103_qwen_swedish_preprocessing.py` no
longer co-owns CLI parsing, run-root lifecycle persistence, and callback
wiring in one module.

## PR Scope

- Add one dedicated runner-status helper module for Task 103 run allocation,
  running/failure/completion status transitions, and heartbeat persistence.
- Refactor the public Task 103 runner to delegate status updates to that helper
  instead of inlining nested callback functions and repeated `write_run_status`
  calls.
- Add direct tests for the extracted helper surface in addition to keeping the
  existing runner-level tests green.
- Preserve behavior and on-disk run/status contracts; this slice is about
  modularity, not changing runtime semantics.

## Deliverables

- [x] One dedicated Task 103 runner-status helper module with module docstring.
- [x] A slimmer public Task 103 runner that delegates lifecycle/status writes
  to the helper.
- [x] Direct focused tests for the extracted helper surface.
- [x] Updated docs memory that records the extraction as the first production
  follow-on after `T132`.

## Acceptance Criteria

- [x] Task 103 run-status and heartbeat writing has one clear module owner
  outside the public CLI entrypoint.
- [x] The public Task 103 runner is smaller and easier to read without behavior
  change.
- [x] Focused tests cover the extracted helper API directly.
- [x] Existing Task 103 runner behavior and persisted status contract remain
  unchanged.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
