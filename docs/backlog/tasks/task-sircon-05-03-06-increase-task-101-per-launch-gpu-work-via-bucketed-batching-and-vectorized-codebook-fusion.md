---
type: task
id: TASK-SIRCON-05-03-06
title: Increase Task 101 per-launch GPU work via bucketed batching and vectorized
  codebook fusion
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
- "[ ] The revised `M0` produces a committed fit-opportunity audit for singleton\n\
  \  rows in the `320-375` codec-frame band."
- "[x] The revised `M0` explicitly distinguishes same-bucket ordering misses from\n\
  \  adjacent-lower-bucket grouping misses on the rebuilt bundle."
- "[x] If the quarantine replay precursor produces only baseline-equivalent\n  plans,\
  \ the task records that null result explicitly and does not launch a\n  duplicate\
  \ Hemma proof."
- '[ ] `M1` lands exactly one targeted batching change promoted by the revised `M0`.'
- '[x] `M1` lands exactly one targeted batching change promoted by the revised `M0`.'
- "[x] If the promoted `M1` candidate is baseline-equivalent or worse in offline\n\
  \  replay, the task records that null result explicitly and does not launch `M2`."
- "[ ] `M2` launches exactly one promoted `M1` candidate and records whether it\n\
  \  stays finite through `30` optimizer steps / first durable checkpoint."
- "[ ] If `M2` stays finite, bounded Hemma evidence shows higher steady-state\n  train\
  \ median GPU busy and better realized occupancy than the stable balanced\n  baseline."
- "[ ] If `M2` stays finite, `M3` records whether ROCm launch/sync overhead\n  dropped\
  \ relative to the March 13 baseline evidence."
- '[x] Throughput profile metadata is surfaced in launch/status/report artifacts.'
retired_ids:
- task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion
---
## Context

Source record: docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md

### Objective

> Raise steady-state GPU utilization without crossing the current numeric
> stability wall by proving one smaller, evidence-backed occupancy uplift on top
> of the last known stable `hemma-throughput-balanced-v1` lane.

### Non-Goals

> - Do not retry the within-bucket best-fit/backfill packer.
> - Do not retry global `640 -> 768` as a promotable default.
> - Do not change model objective or add in-training evaluation.
> - Do not weaken checkpoint durability guarantees.
> - Do not claim saturation success without monitor-backed evidence.
> - Do not localize the denser-lane `NaN` here; that remains owned by `T179`.

## Decision And Assumption Ledger

## Story Contract Slice

### PR Scope

> - Restructure `T172` around the revised bounded experiment matrix:
>   - `M0`: offline fit-opportunity audit over the singleton tail
>   - `M1`: implement exactly one targeted batching change promoted by `M0`
>   - `M2`: one finite Hemma uplift proof on that promoted candidate
>   - `M3`: one post-change ROCm attribution proof if `M2` stays finite
> - Keep the old greedy one-open-batch packer as the only promotable default
>   packer until a smaller bounded uplift is proven.
> - Add committed offline analysis surfaces that can distinguish:
>   - same-bucket missed fits caused by greedy ordering
>   - adjacent-lower-bucket missed fits caused by the current bucket signal
> - Keep launch/report metadata truthful:
>   - explicit profile label
>   - explicit batch-policy settings
>   - explicit batch-occupancy evidence
> - Record failed knobs and non-promotable candidates inside this task instead of
>   silently carrying them forward.

## Contract Inputs

## Plan

### Experiment Matrix

> ### `M0` Offline fit-opportunity audit
>
> - Run a committed batch-plan analysis surface against the rebuilt bundle train
>   manifest with the stable:
>   - old greedy one-open-batch packer
>   - `max_codec_frames_per_batch=640`
>   - no optimizer or runtime changes
> - Audit singleton rows in the problematic `320-375` codec-frame band.
> - For each audited singleton row, record:
>   - whether a fitting partner exists later in the same bucket under unchanged
>     frame/token caps
>   - whether a fitting partner exists in the adjacent lower bucket under those
>     same caps
> - Use that discriminator to choose the smallest next change:
>   - same-bucket fits dominate -> narrow local lookahead candidate
>   - adjacent-lower-bucket fits dominate -> frame-primary / retuned bucketing
>     candidate
>   - neither dominates -> batching-only uplift is weaker than hoped and the task
>     should record that explicitly
>
> ### `M1` Targeted candidate implementation
>
> - Land exactly one targeted batching change promoted by `M0`.
> - Keep:
>   - old greedy packer semantics everywhere outside the targeted intervention
>   - global codec-frame budget `640`
>   - no optimizer or runtime changes
> - Do not mix multiple uplift ideas in the same code slice.
>
> ### `M2` Finite uplift proof on Hemma
>
> - Launch the promoted `M1` candidate through the canonical detached
>   `qwen-train launch` surface.
> - Keep:
>   - train/eval manifest family pairing aligned to the rebuilt bundle reality
>   - `batch_size=8`
>   - unchanged `640` global codec-frame budget
>   - unchanged LR, optimizer, precision, and checkpoint policy
> - Bound the proof at:
>   - `max_steps=30`
>   - `checkpoint_interval_steps=30`
> - Accept only if:
>   - the run stays finite through the bounded window
>   - mean batch size beats the stable balanced baseline
>   - singleton share beats the stable balanced baseline
>   - steady-state train GPU median beats the stable balanced baseline
>
> ### `M3` Post-change ROCm attribution proof
>
> - Only run this if `M2` yields a finite candidate worth attributing.
> - Capture one bounded ROCm proof on the best finite candidate to verify whether
>   higher occupancy actually reduces launch/sync dominance.

## Implementation Steps

## Proof

### Deliverables

> - [x] Bucketed non-`batch_size=1` throughput profile(s) implemented.
> - [x] Vectorized/fused codebook path replaces the current fragmented loop.
> - [x] Destabilizing best-fit packer reverted after Hemma isolation proved it
>   breaks the stable balanced lane.
> - [x] Committed offline batch-plan analysis surface exists for `M0`.
> - [ ] One evidence-backed smaller uplift candidate chosen from the revised `M0`.
> - [x] One bounded quarantine replay precursor was completed and explicitly rejected as a no-op
>   for the initial quarantine threshold.
> - [x] The revised `M0` fit-opportunity audit completed and selected bucket-signal
>   retuning as the next promoted `M1` direction.
> - [x] One targeted `M1` batching change implemented from the revised `M0`.
> - [ ] One finite `M2` Hemma uplift proof completed or rejected with evidence.
> - [ ] One evidence-backed default profile chosen for follow-on saturation runs.

### Validation

> - [x] `pdm run format-all`
> - [x] `pdm run lint-fix`
> - [x] `pdm run typecheck-all`
> - [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_bundles.py tests/sir_convert_a_lot/ml/qwen/training/test_batching.py tests/sir_convert_a_lot/ml/qwen/training/test_codebook_fusion.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py`
> - [x] `pdm run validate-tasks`
> - [x] `pdm run validate-docs`
> - [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
> - [ ] `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.cli.ml.qwen_batch_plan --pilot-bundle-root <rebuilt_bundle_root> --fit-audit-codec-frame-band-min 320 --fit-audit-codec-frame-band-max 375`
> - [ ] `pdm run run-hemma -- pdm run qwen-train launch ...` for the promoted `M1` candidate
> - [ ] If `M2` stays finite, one bounded ROCm attribution proof written under
>   `build/verification/`.

## Validation

## Stop Conditions

## Lessons Learned

### Why This Exists

> `T162` and the March 13 live-pipeline reference doc show the lane remains
> launch/sync heavy on Hemma. The current rebuilt-bundle stable default is now
> `hemma-throughput-balanced-v1`, but that lane still tops out far below
> saturation because:
>
> - mean realized batch size is only `1.4065934065934067`
> - the batch histogram is dominated by `1`-row and `2`-row batches
> - text-token budget is not the active limiter
> - codec-frame budget is the active limiter
>
> Earlier uplift attempts are now disproven:
>
> - the within-bucket best-fit/backfill packer destabilized even plain balanced
>   at optimizer step `4`
> - the old greedy packer plus global `640 -> 768` frame budget still failed
>   with a real `NaN` at optimizer step `21`
>
> So the next bounded `T172` slice must stay inside the proven stable envelope
> and test smaller batching-policy changes first.

### Cross-Task Boundary

> - `T172` owns the stable-lane occupancy uplift experiments above.
> - `T179` owns the denser-lane non-finite-loss localization experiment:
>   - add first-non-finite component-loss and density artifacts
>   - rerun the known unstable old-packer `768` lane for localization

## Notes

## Plan Document Review

## Implementation Review
