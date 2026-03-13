---
id: task-158-make-high-resolution-hemma-resource-monitoring-default-for-long-task-101-qwen-runs
title: Make high-resolution Hemma resource monitoring default for long Task 101 Qwen runs
type: task
status: completed
priority: critical
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-116-expand-rixvox-staging-and-run-a-sustained-detached-row-processing-window-for-the-bounded-hemma-pilot.md
  - docs/backlog/tasks/task-157-add-truthful-live-heartbeat-and-phase-accounting-to-the-task-101-qwen-pilot-runtime.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - https://www.mlflow.org/docs/latest/ml/tracking/system-metrics/
labels:
  - qwen
  - monitoring
  - gpu
  - hemma
  - resource-monitor
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make high-resolution resource monitoring the default posture for long Task 101
Hemma runs so the team always has GPU-busy, VRAM, CPU, and RAM evidence for
the same training window.

## Why This Exists

The `2026-03-13` live analysis only discovered the real throughput problem
after manually launching the detached Task 116 resource monitor. The first
summary showed:

- `gpu_busy_percent_median = 5`
- `gpu_busy_percent_max = 12`
- `gpu_memory_used_percent_median = 68`

That signal is too important to remain opt-in operator trivia.

## PR Scope

- Make the Task 101 long-run path auto-launch or explicitly companion-launch a
  resource monitor using the committed Task 116 surface.
- Use `<= 1.0` second sampling for any run intended as saturation evidence.
- Persist the monitor launch id and launch root into Task 101 metadata so the
  operator can discover the monitor run from Task 101 status alone.
- Extend the monitor summary or Task 101 report path to compute:
  - overall GPU-busy statistics
  - steady-state non-checkpoint training statistics
  - checkpoint-window statistics
- Keep the monitor path detached and host-side so it does not depend on
  in-container tracker support.

## Non-Goals

- Do not replace MLflow system metrics.
- Do not make the long-run monitor a fragile attached shell job.
- Do not change dataloader or checkpoint internals here.

## Deliverables

- [x] Long Task 101 launches emit a discoverable sibling resource-monitor run.
- [x] The default high-resolution monitor interval is codified for saturation
  evidence.
- [x] Task 101 status/report surfaces expose the monitor launch root.
- [x] Summary output distinguishes steady-state training from checkpoint-save
  windows.

## Acceptance Criteria

- [x] A long Task 101 launch automatically produces a linked resource-monitor
  run or emits one explicit governed command surface that is impossible to
  overlook.
- [x] Saturation-evidence runs sample at `<= 1.0` second resolution.
- [x] Operators can inspect one Task 101 launch and immediately discover the
  corresponding monitor launch id and summary.
- [x] The monitor summary is rich enough to compute the canonical
  `>= 90%` median GPU-busy gate over steady-state non-checkpoint windows.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task116_hemma_resource_monitor.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_resource_monitor.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma proof shows the monitor launch and summary linked from the
  corresponding Task 101 run.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
