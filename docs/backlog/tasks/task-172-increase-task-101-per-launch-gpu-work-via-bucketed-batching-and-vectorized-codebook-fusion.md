---
id: task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion
title: Increase Task 101 per-launch GPU work via bucketed batching and vectorized codebook fusion
type: task
status: proposed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-160-tune-the-task-101-qwen-dataloader-and-device-transfer-path-for-gpu-saturation.md
  - docs/backlog/tasks/task-162-add-bounded-pytorch-and-rocm-profiling-surfaces-for-task-101-qwen-bottleneck-attribution.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
labels:
  - qwen
  - training
  - throughput
  - gpu
  - optimization
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Raise steady-state GPU utilization by increasing useful work per launch and
reducing Python-side kernel fragmentation in the Task 101 training step.

## Why This Exists

`T162` traces show host-launch/sync overhead dominating the current lane. The
current `batch_size=1` default and per-codebook Python loops generate too many
small launches for the target saturation posture.

## PR Scope

- Add a bounded throughput profile that is not anchored to `batch_size=1`:
  - token/frame-budgeted batching policy
  - length bucketing for lower padding waste
  - bounded default candidate for the Hemma lane
- Replace Python-side per-codebook embedding loops with a vectorized/fused
  implementation that reduces launch count and synchronization points.
- Keep launch contract truthful:
  - explicit profile label in launch/status/report metadata
  - explicit recorded batch policy settings.
- Produce one bounded Hemma sweep over at least two candidate throughput
  profiles and keep one evidence-backed default.

## Non-Goals

- Do not change model objective or add in-training evaluation.
- Do not weaken checkpoint durability guarantees.
- Do not claim saturation success without monitor-backed evidence.

## Deliverables

- [ ] Bucketed non-`batch_size=1` throughput profile(s) implemented.
- [ ] Vectorized/fused codebook path replaces the current fragmented loop.
- [ ] One evidence-backed default profile chosen for follow-on saturation runs.

## Acceptance Criteria

- [ ] Bounded Hemma evidence shows higher steady-state train median GPU busy
  than the `T161/T162` baseline.
- [ ] ROCm profiling confirms reduced launch/sync overhead relative to the
  baseline task evidence.
- [ ] Throughput profile metadata is surfaced in launch/status/report artifacts.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_qwen_training_dataloader_tuning.py tests/sir_convert_a_lot/test_qwen_training_profiling.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma profile sweep evidence written under `build/verification/`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
