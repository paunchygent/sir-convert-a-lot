---
id: task-161-add-ref-mel-caching-and-a-promotion-decision-for-precomputed-task-101-qwen-reference-mels
title: Add ref-mel caching and a promotion decision for precomputed Task 101 Qwen reference mels
type: task
status: in_progress
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-118-profile-the-qwen-finetuning-dataloader-and-decide-whether-to-precompute-ref-mels.md
  - docs/backlog/tasks/task-160-tune-the-task-101-qwen-dataloader-and-device-transfer-path-for-gpu-saturation.md
  - docs/backlog/tasks/task-164-persist-precomputed-task-101-qwen-reference-mels-in-the-pilot-bundle-and-training-manifest-contract.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
labels:
  - qwen
  - finetuning
  - ref-mel
  - caching
  - throughput
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the most obvious duplicate `ref_mel` work from the hot training path by
adding runtime caching keyed to stable reference-audio inputs, and leave the
team with an explicit evidence-backed decision on whether bundle-level
precomputed mels are still needed.

## Why This Exists

The current Task 101 dataset path computes `ref_mel` inside `__getitem__` even
though the same canonical per-speaker `ref_audio` anchors are reused across
many rows. That is likely wasteful, but the least disruptive first fix is a
runtime cache rather than an immediate artifact-contract expansion.

## PR Scope

- Add bounded runtime `ref_mel` caching keyed by canonical `ref_audio` path or
  equivalent stable bundle-local identity.
- Record cache hits, misses, and hit rate as machine-readable metrics and
  tracker scalars.
- Verify that the cache survives normal dataloader iteration without creating
  correctness drift or unbounded memory growth.
- Produce one bounded Hemma comparison between cache-off and cache-on.
- Write down the promotion decision:
  - cache alone is sufficient for now, or
  - bundle-level precomputed mels are still needed and `T164` should proceed.

## Implementation Plan (Concrete)

Code changes:

- add `scripts/devops/qwen_finetuning_patches/sft_12hz_ref_mel_cache.py`
  - bounded cache keyed by stable canonical `ref_audio` identity
  - explicit stats payload: `cache_hits`, `cache_misses`, `cache_size`, `hit_rate`
- update `scripts/devops/qwen_finetuning_patches/dataset.py`
  - resolve canonical key per row
  - bypass duplicate mel extraction through the cache
- update `scripts/devops/qwen_finetuning_patches/sft_12hz.py`
  - add cache controls (`enabled`, `max_items`)
  - persist cache stats into `TrainingSummary`
- update tracker/status surfaces so cache stats are visible:
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_tracking.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe_reporting.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_metadata.py`
- update Task 101 launch/runtime contracts for cache settings:
  - `scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime_contract.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe.py`
- add governed comparison surface:
  - `scripts/sir_convert_a_lot/devops/run_task161_hemma_ref_mel_cache_comparison.py`

Test changes:

- add `tests/sir_convert_a_lot/test_qwen_training_ref_mel_cache.py`
  - cache-key correctness
  - bounded-size behavior
  - hit/miss accounting
- extend `tests/sir_convert_a_lot/test_task101_qwen_pilot.py`
  - parser/command propagation for cache flags

Hemma evidence path:

- `build/verification/task-161-ref-mel-cache-comparison/<run-id>/`

## Non-Goals

- Do not expand the pilot-bundle manifest contract in this task.
- Do not silently persist large new artifacts under `build/reference/` yet.
- Do not close the MIOpen lane here.

## Deliverables

- [x] Runtime `ref_mel` cache added to the Task 101 training path.
- [x] Cache-hit metrics are visible in machine-readable output or trackers.
- [ ] Bounded Hemma evidence compares cache-off versus cache-on behavior.
- [ ] A documented go/no-go decision exists for `T164`.

## Acceptance Criteria

- [x] Duplicate rows sharing the same canonical `ref_audio` no longer
  recompute `ref_mel` blindly during the same run.
- [ ] The cache path measurably improves throughput or GPU-busy behavior over
  the uncached baseline.
- [ ] The task concludes with one explicit statement:
  - “cache-only is sufficient for the current story”, or
  - “proceed with `T164` bundle-level precomputed mels”.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_qwen_training_ref_mel_cache.py tests/sir_convert_a_lot/test_task161_qwen_ref_mel_cache_comparison.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma comparison records cache hit rate and resource-summary
  deltas.

## Checklist

- [x] Implementation complete
- [ ] Validation complete
- [x] Docs updated
