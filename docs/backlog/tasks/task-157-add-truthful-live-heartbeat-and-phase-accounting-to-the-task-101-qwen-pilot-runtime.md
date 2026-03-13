---
id: task-157-add-truthful-live-heartbeat-and-phase-accounting-to-the-task-101-qwen-pilot-runtime
title: Add truthful live heartbeat and phase accounting to the Task 101 Qwen pilot runtime
type: task
status: proposed
priority: critical
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-156-activate-first-class-mlflow-and-accelerate-tracking-for-task-101-qwen-training.md
  - docs/backlog/tasks/task-158-make-high-resolution-hemma-resource-monitoring-default-for-long-task-101-qwen-runs.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - heartbeat
  - status
  - monitoring
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Turn Task 101 `status.json` from mostly launch-time metadata into a truthful
live heartbeat surface that records current progress, current phase, and the
latest known runtime state during training.

## Why This Exists

The live Task 101 run on `2026-03-13` kept `pilot_status.updated_at` pinned
near launch time even while steps and checkpoints advanced. That makes the
status contract misleading and prevents phase-aware monitor analysis.

## PR Scope

- Update the in-container Task 101 runtime to persist a bounded live heartbeat
  during training.
- Record progress fields such as:
  - current epoch
  - current step
  - latest known raw loss
  - latest known smoothed loss
  - latest durable checkpoint step
  - latest durable checkpoint timestamp
  - tracker run ids from `T156`
- Add explicit phase accounting for at least:
  - `startup`
  - `train`
  - `checkpoint-save`
  - `signal-stop`
  - `completed`
  - `failed`
- Keep the status artifact backward-compatible enough that older launches still
  inspect cleanly.
- Surface the new live fields through the Task 101 status CLI and markdown
  rendering path.

## Non-Goals

- Do not replace MLflow/TensorBoard with JSON-heartbeat metrics.
- Do not launch the resource monitor here.
- Do not change training hyperparameters or checkpoint policy in this slice.

## Deliverables

- [ ] Task 101 writes bounded live heartbeat updates during training.
- [ ] Phase accounting is persisted in machine-readable form.
- [ ] Status inspection surfaces expose the new live fields.
- [ ] Backward-compatible tests cover old and new status payloads.

## Acceptance Criteria

- [ ] During a bounded Task 101 run, `status.json` updates while training is
  still in progress rather than only at launch and terminal completion.
- [ ] The live status artifact exposes current step, current epoch, latest loss,
  smoothed loss, current phase, and latest checkpoint metadata.
- [ ] The CLI status output and metadata parsers stay truthful for both new and
  historical launches.
- [ ] The resulting phase surface is rich enough for the resource-monitor lane
  to exclude checkpoint-save windows from the canonical steady-state GPU-busy
  gate.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma proof shows `status.json` changing at runtime.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
