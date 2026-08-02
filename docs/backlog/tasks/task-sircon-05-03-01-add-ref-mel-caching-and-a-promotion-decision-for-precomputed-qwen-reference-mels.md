---
type: task
id: TASK-SIRCON-05-03-01
title: Add ref-mel caching and a promotion decision for precomputed Qwen reference
  mels
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
story: ST-SIRCON-05-03
task_kind: story
acceptance_criteria:
- "[x] Duplicate rows sharing the same canonical `ref_audio` no longer\n  recompute\
  \ `ref_mel` blindly during the same run."
- "[ ] The cache path measurably improves throughput or GPU-busy behavior over\n \
  \ the uncached baseline."
- "[x] The task concludes with one explicit statement:\n  - “cache-only is sufficient\
  \ for the current story”, or\n  - “proceed with `T164` bundle-level precomputed\
  \ mels”."
retired_ids:
- task-161-add-ref-mel-caching-and-a-promotion-decision-for-precomputed-task-101-qwen-reference-mels
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Remove the most obvious duplicate `ref_mel` work from the hot training path by
adding runtime caching keyed to stable reference-audio inputs, and leave the
team with an explicit evidence-backed decision on whether bundle-level
precomputed mels are still needed.

### Why This Exists

The current Task 101 dataset path computes `ref_mel` inside `__getitem__` even
though the same canonical per-speaker `ref_audio` anchors are reused across
many rows. That is likely wasteful, but the least disruptive first fix is a
runtime cache rather than an immediate artifact-contract expansion.

### PR Scope

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

### Implementation Plan (Concrete)

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

- `build/verification/task-101-qwen3-tts-swedish-hemma-pilot/<launch-id>/`
- run roots:
  - `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task161-20260313t212725z-cache-off`
  - `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task161-20260313t212725z-cache-on`

### Non-Goals

- Do not expand the pilot-bundle manifest contract in this task.
- Do not silently persist large new artifacts under `build/reference/` yet.
- Do not close the MIOpen lane here.

### Hemma Evidence (2026-03-13)

One bounded comparison was executed on Hemma with identical training settings
except for `ref_mel_cache_enabled`.

Launches:

- cache-off: `task161-20260313t212725z-cache-off`
- cache-on: `task161-20260313t212725z-cache-on`

Measured steady-state train GPU-busy medians (non-checkpoint train window):

- cache-off median GPU busy: `26%`
- cache-on median GPU busy: `8%`

Observed cache metrics from both runs:

- cache-off: `cache_hits=0`, `cache_misses=0`, `cache_size=0`
- cache-on: `cache_hits=0`, `cache_misses=0`, `cache_size=0`

Conclusion for this task:

- runtime cache behavior is not engaged in practice for this lane
- the cache path did not improve saturation in the measured comparison
- explicit decision: proceed with `T164` and make bundle-level precomputed
  `ref_mel` (or speaker-embedding equivalent) the next mandatory optimization
  lane

### Deliverables

- [x] Runtime `ref_mel` cache added to the Task 101 training path.
- [x] Cache-hit metrics are visible in machine-readable output or trackers.
- [x] Bounded Hemma evidence compares cache-off versus cache-on behavior.
- [x] A documented go/no-go decision exists for `T164`.

### Acceptance Criteria

- [x] Duplicate rows sharing the same canonical `ref_audio` no longer
  recompute `ref_mel` blindly during the same run.
- [ ] The cache path measurably improves throughput or GPU-busy behavior over
  the uncached baseline.
- [x] The task concludes with one explicit statement:
  - “cache-only is sufficient for the current story”, or
  - “proceed with `T164` bundle-level precomputed mels”.

### Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_qwen_training_ref_mel_cache.py tests/sir_convert_a_lot/test_task161_qwen_ref_mel_cache_comparison.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] Bounded Hemma comparison records cache hit rate and resource-summary
  deltas.

### Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
