---
id: task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion
title: Increase Task 101 per-launch GPU work via bucketed batching and vectorized codebook fusion
type: task
status: in_progress
priority: high
created: '2026-03-13'
last_updated: '2026-03-14'
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

## Implementation Notes

- The local implementation slice now introduces explicit throughput profiles,
  with the current aggressive candidate centered on `max_batch_size=8` plus
  token/frame budgets and deterministic length bucketing.
- The patched trainer now uses a custom batch sampler instead of a plain
  shuffled fixed-size `DataLoader` batch policy.
- Launch, status, and terminal report artifacts now surface truthful
  throughput-profile metadata.
- The hot training loop no longer performs iterative Python-side auxiliary
  codebook accumulation inline; that logic now lives in a dedicated fusion
  helper and aggregates the auxiliary codebook embeddings in one summed path.
- Hemma profile-sweep evidence and default-profile selection are still pending.

## Current Progress

- The rebuilt-bundle aggressive proof remains numerically unstable:
  - `task-175-throughput-proof-20260314c/20260314T193710Z`
  - failed at `optimizer_step=4` with a real `NaN` loss after the failure
    reporting surfaces were corrected
- The rebuilt-bundle balanced proof completed cleanly:
  - `task-175-throughput-proof-20260314d-balanced/20260314T195507Z`
  - `optimizer_steps_completed=91`
  - steady-state train GPU median `37%`
  - mean batch size `1.4065934065934067`
  - realized max batch size `7`
  - batch histogram dominated by `1`-row and `2`-row batches
- The balanced proof shows the lane is stable but still badly occupancy-bound:
  - text-token budget is not the active limiter
  - codec-frame budget is the active limiter
  - the current bucketed sampler still wastes capacity because it keeps only
    one open batch per bucket and cannot backfill earlier partially filled
    batches
- The next T172 implementation slice therefore targets the balanced lane
  first, before another aggressive retry:
  - add a `hemma-throughput-balanced-plus-v1` profile with a modestly higher
    codec-frame budget
  - replace the current one-open-batch greedy packing logic with a deterministic
    best-fit style packer inside each bucket so compatible rows can backfill
    partially filled batches
- That local implementation slice is now landed:
  - `hemma-throughput-balanced-plus-v1` is available as a bounded profile
    between the current balanced and aggressive lanes
  - the bucketed sampler now performs deterministic best-fit backfilling within
    each bucket instead of finalizing the current batch as soon as the next row
    does not fit
  - focused local validation passed for batching, orchestrator, reporting,
    trainer, and train-loop surfaces

## Deliverables

- [x] Bucketed non-`batch_size=1` throughput profile(s) implemented.
- [x] Vectorized/fused codebook path replaces the current fragmented loop.
- [ ] One evidence-backed default profile chosen for follow-on saturation runs.

## Acceptance Criteria

- [ ] Bounded Hemma evidence shows higher steady-state train median GPU busy
  than the `T161/T162` baseline.
- [ ] ROCm profiling confirms reduced launch/sync overhead relative to the
  baseline task evidence.
- [x] Throughput profile metadata is surfaced in launch/status/report artifacts.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_bundles.py tests/sir_convert_a_lot/ml/qwen/training/test_batching.py tests/sir_convert_a_lot/ml/qwen/training/test_codebook_fusion.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma profile sweep evidence written under `build/verification/`.

## Checklist

- [x] Implementation complete
- [ ] Validation complete
- [x] Docs updated
