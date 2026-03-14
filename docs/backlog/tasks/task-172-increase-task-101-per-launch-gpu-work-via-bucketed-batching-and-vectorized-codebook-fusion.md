---
id: task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion
title: Increase Task 101 per-launch GPU work via bucketed batching and vectorized codebook fusion
type: task
status: in_progress
priority: high
created: '2026-03-13'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-160-tune-the-task-101-qwen-dataloader-and-device-transfer-path-for-gpu-saturation.md
  - docs/backlog/tasks/task-162-add-bounded-pytorch-and-rocm-profiling-surfaces-for-task-101-qwen-bottleneck-attribution.md
  - docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md
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

Raise steady-state GPU utilization without crossing the current numeric
stability wall by proving one smaller, evidence-backed occupancy uplift on top
of the last known stable `hemma-throughput-balanced-v1` lane.

## Why This Exists

`T162` and the March 13 live-pipeline reference doc show the lane remains
launch/sync heavy on Hemma. The current rebuilt-bundle stable default is now
`hemma-throughput-balanced-v1`, but that lane still tops out far below
saturation because:

- mean realized batch size is only `1.4065934065934067`
- the batch histogram is dominated by `1`-row and `2`-row batches
- text-token budget is not the active limiter
- codec-frame budget is the active limiter

Earlier uplift attempts are now disproven:

- the within-bucket best-fit/backfill packer destabilized even plain balanced
  at optimizer step `4`
- the old greedy packer plus global `640 -> 768` frame budget still failed
  with a real `NaN` at optimizer step `21`

So the next bounded `T172` slice must stay inside the proven stable envelope
and test smaller batching-policy changes first.

## PR Scope

- Restructure `T172` around the architect-guided bounded experiment matrix:
  - `M0`: offline occupancy replay against the rebuilt bundle
  - `M1`: one finite Hemma uplift proof on the best offline candidate
  - `M3`: one post-change ROCm attribution proof if `M1` stays finite
- Keep the old greedy one-open-batch packer as the only promotable default
  packer until a smaller bounded uplift is proven.
- Add smaller, policy-level uplift candidates that do not repeat the already
  disproven knobs:
  - long-row singleton quarantine under the stable `640` codec-frame cap
  - optional upper-tail bucket refinement under the same stable cap
- Keep launch/report metadata truthful:
  - explicit profile label
  - explicit batch-policy settings
  - explicit batch-occupancy evidence
- Record failed knobs and non-promotable candidates inside this task instead of
  silently carrying them forward.

## Non-Goals

- Do not retry the within-bucket best-fit/backfill packer.
- Do not retry global `640 -> 768` as a promotable default.
- Do not change model objective or add in-training evaluation.
- Do not weaken checkpoint durability guarantees.
- Do not claim saturation success without monitor-backed evidence.
- Do not localize the denser-lane `NaN` here; that remains owned by `T179`.

## Experiment Matrix

### `M0` Offline occupancy replay

- Run a committed batch-plan analysis surface against the rebuilt bundle train
  manifest.
- Compare exactly these profiles:
  - `hemma-throughput-balanced-v1`
  - `hemma-throughput-balanced-quarantine-v1`
  - `hemma-throughput-balanced-quarantine-tail-v1`
- Keep all of them on:
  - old greedy one-open-batch packer
  - `max_codec_frames_per_batch=640`
  - no optimizer or runtime changes
- Compare:
  - mean batch size
  - singleton-batch share
  - two-row-batch share
  - peak batch codec frames
- Promote exactly one candidate into `M1`.

### `M1` Finite uplift proof on Hemma

- Launch the promoted `M0` candidate through the canonical detached
  `qwen-train launch` surface.
- Keep:
  - train/eval manifest family pairing aligned to the rebuilt bundle reality
  - `batch_size=8`
  - old greedy packer
  - global codec-frame budget `640`
  - no LR or optimizer changes
- Bound the proof at:
  - `max_steps=30`
  - `checkpoint_interval_steps=30`
- Accept only if:
  - the run stays finite through the bounded window
  - mean batch size beats the stable balanced baseline
  - steady-state train GPU median beats the stable balanced baseline

### `M3` Post-change ROCm attribution proof

- Only run this if `M1` yields a finite candidate worth attributing.
- Capture one bounded ROCm proof on the best finite candidate to verify whether
  higher occupancy actually reduces launch/sync dominance.

## Cross-Task Boundary

- `T172` owns the stable-lane occupancy uplift experiments above.
- `T179` owns the denser-lane non-finite-loss localization experiment:
  - add first-non-finite component-loss and density artifacts
  - rerun the known unstable old-packer `768` lane for localization

## Current Progress

- The rebuilt-bundle balanced proof completed cleanly:
  - `task-175-throughput-proof-20260314d-balanced/20260314T195507Z`
  - `optimizer_steps_completed=91`
  - steady-state train GPU median `37%`
  - mean batch size `1.4065934065934067`
  - realized max batch size `7`
  - batch histogram dominated by `1`-row and `2`-row batches
- The stable balanced proof shows the lane is still badly occupancy-bound:
  - text-token budget is not the active limiter
  - codec-frame budget is the active limiter
  - the stable default remains the old greedy one-open-batch packer
- The aggressive rebuilt-bundle proof remains numerically unstable:
  - `task-175-throughput-proof-20260314c/20260314T193710Z`
  - failed at `optimizer_step=4` with a real `NaN`
- The attempted occupancy-lift knobs from the earlier local slice are now
  recorded as non-promotable:
  - `hemma-throughput-balanced-plus-v1` failed at `optimizer_step=44` in
    `task-175-throughput-proof-20260314e-balanced-plus/20260314T204711Z`
  - the current-code balanced isolation run failed at `optimizer_step=4` in
    `task-175-throughput-proof-20260314f-balanced-current-packer/20260314T210257Z`
- That isolation proved the within-bucket best-fit/backfill packer is itself a
  destabilizer:
  - old balanced + old greedy packer completed
  - old balanced budget + best-fit packer failed immediately
- The old-packer `768` isolation run is also recorded:
  - `task-175-throughput-proof-20260314g-balanced-plus-old-packer/20260314T212920Z`
  - entered `train`, survived well past the old step-`4` crash boundary, and
    still failed with a real `NaN` at `optimizer_step=21`
- So both prior uplift knobs are now explicitly non-promotable:
  - best-fit/backfill packer
  - global `640 -> 768` codec-frame-budget uplift
- The new local implementation slice for this task adds:
  - committed offline batch-plan analysis surface `qwen-batch-plan`
  - bounded quarantine candidate profile under the stable `640` cap
  - bounded quarantine plus upper-tail bucket candidate under the same cap
- `M0` has now been executed against the rebuilt bundle:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/verification/task-172-batch-plan-analysis-20260315a/20260314T231848Z`
  - all three compared profiles produced identical occupancy:
    - `hemma-throughput-balanced-v1`
    - `hemma-throughput-balanced-quarantine-v1`
    - `hemma-throughput-balanced-quarantine-tail-v1`
  - mean batch size remained `1.4065934065934067`
  - singleton share remained `0.6675824175824175`
  - two-row share remained `0.2857142857142857`
  - peak batch codec frames remained `640`
  - quarantined row count remained `0`
- The key `M0` finding is that the architect's first quarantine threshold does
  not engage on this rebuilt bundle:
  - maximum per-row codec frames are only `375`
  - so the proposed `>= 480` singleton rule never fires
  - the upper-tail boundary refinement also makes no difference under the
    current combined-cost bucket key
- `M1` is therefore intentionally blocked for the moment:
  - there is no promoted occupancy candidate yet because `M0` produced only
    baseline-equivalent plans
  - launching a duplicate Hemma proof would not answer a new question

## Deliverables

- [x] Bucketed non-`batch_size=1` throughput profile(s) implemented.
- [x] Vectorized/fused codebook path replaces the current fragmented loop.
- [x] Destabilizing best-fit packer reverted after Hemma isolation proved it
  breaks the stable balanced lane.
- [x] Committed offline batch-plan analysis surface exists for `M0`.
- [ ] One evidence-backed smaller uplift candidate chosen from `M0`.
- [x] One bounded `M0` replay was completed and explicitly rejected as a no-op
  for the initial quarantine threshold.
- [ ] One finite `M1` Hemma uplift proof completed or rejected with evidence.
- [ ] One evidence-backed default profile chosen for follow-on saturation runs.

## Acceptance Criteria

- [ ] `M0` produces a committed occupancy report for the rebuilt bundle that
  compares baseline, quarantine, and quarantine-tail candidates under the same
  stable `640` codec-frame cap.
- [x] If `M0` produces only baseline-equivalent plans, the task records that
  null result explicitly and does not launch a duplicate `M1` proof.
- [ ] `M1` launches exactly one promoted `M0` candidate and records whether it
  stays finite through `30` optimizer steps / first durable checkpoint.
- [ ] If `M1` stays finite, bounded Hemma evidence shows higher steady-state
  train median GPU busy and better realized occupancy than the stable balanced
  baseline.
- [ ] If `M1` stays finite, `M3` records whether ROCm launch/sync overhead
  dropped relative to the March 13 baseline evidence.
- [x] Throughput profile metadata is surfaced in launch/status/report artifacts.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_bundles.py tests/sir_convert_a_lot/ml/qwen/training/test_batching.py tests/sir_convert_a_lot/ml/qwen/training/test_codebook_fusion.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run run-hemma -- pdm run qwen-batch-plan --pilot-bundle-root <rebuilt_bundle_root>`
- [ ] `pdm run run-hemma -- pdm run qwen-train launch ... --throughput-profile-label hemma-throughput-balanced-quarantine-v1`
- [ ] If `M1` stays finite, one bounded ROCm attribution proof written under
  `build/verification/`.

## Checklist

- [x] Implementation complete
- [ ] Validation complete
- [x] Docs updated
