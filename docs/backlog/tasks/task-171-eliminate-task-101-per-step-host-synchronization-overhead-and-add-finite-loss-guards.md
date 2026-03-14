---
id: task-171-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards
title: Eliminate Task 101 per-step host synchronization overhead and add finite-loss guards
type: task
status: proposed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-162-add-bounded-pytorch-and-rocm-profiling-surfaces-for-task-101-qwen-bottleneck-attribution.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - training
  - throughput
  - observability
  - rocm
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove avoidable host-side synchronization from the Task 101 hot path and add
finite-loss guardrails so saturation evidence is generated from numerically
valid training windows.

## Why This Exists

`T162` profiling evidence shows heavy host/API overhead (`hipLaunchKernel`,
`hipMemcpyWithStream`, `hipEventSynchronize`) and persistent `NaN` loss in the
same lane. Per-iteration scalar reads and status/tracker writes currently add
avoidable synchronization and orchestration overhead.

## PR Scope

- Decimate hot-path scalar extraction:
  - avoid per-iteration `loss.item()` as the default path
  - log scalar loss at bounded cadence on optimizer-step boundaries
- Decimate tracker/status writes:
  - emit heartbeat/tracker payloads every `N` optimizer steps (default `20`)
  - preserve immediate writes for phase changes and terminal transitions
- Add async or buffered status-write surface so the training loop is not blocked
  by JSON writes on every optimizer iteration.
- Add finite-loss guard:
  - fail fast when loss becomes non-finite for a bounded consecutive threshold
  - persist explicit failed status reason and stop acceptance measurement.
- Keep truthful observability:
  - no silent loss of phase history
  - no silent suppression of tracker metadata.

## Non-Goals

- Do not redesign dataloader batching in this task.
- Do not add bundle-level precomputed `ref_mel` artifacts in this task.
- Do not change the story-level saturation threshold in this task.

## Deliverables

- [ ] Training loop no longer performs default per-iteration scalar-sync logging.
- [ ] Status/tracker emission cadence is bounded and documented.
- [ ] Finite-loss guard stops `NaN` runs and marks them as invalid for
  saturation acceptance.

## Acceptance Criteria

- [ ] Bounded Hemma run shows materially lower HIP synchronization overhead
  relative to the `T162` baseline.
- [ ] Training status/report artifacts remain truthful under the decimated
  heartbeat/logging cadence.
- [ ] At least one bounded Hemma run completes with finite loss values across
  the measured steady-state window.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_qwen_training_tracking.py tests/sir_convert_a_lot/test_task101_qwen_status_reporter.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] One bounded Hemma evidence run records finite loss and updated monitor
  summary under `build/verification/`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
