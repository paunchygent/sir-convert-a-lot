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

- Restructure `T172` around the revised bounded experiment matrix:
  - `M0`: offline fit-opportunity audit over the singleton tail
  - `M1`: implement exactly one targeted batching change promoted by `M0`
  - `M2`: one finite Hemma uplift proof on that promoted candidate
  - `M3`: one post-change ROCm attribution proof if `M2` stays finite
- Keep the old greedy one-open-batch packer as the only promotable default
  packer until a smaller bounded uplift is proven.
- Add committed offline analysis surfaces that can distinguish:
  - same-bucket missed fits caused by greedy ordering
  - adjacent-lower-bucket missed fits caused by the current bucket signal
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

### `M0` Offline fit-opportunity audit

- Run a committed batch-plan analysis surface against the rebuilt bundle train
  manifest with the stable:
  - old greedy one-open-batch packer
  - `max_codec_frames_per_batch=640`
  - no optimizer or runtime changes
- Audit singleton rows in the problematic `320-375` codec-frame band.
- For each audited singleton row, record:
  - whether a fitting partner exists later in the same bucket under unchanged
    frame/token caps
  - whether a fitting partner exists in the adjacent lower bucket under those
    same caps
- Use that discriminator to choose the smallest next change:
  - same-bucket fits dominate -> narrow local lookahead candidate
  - adjacent-lower-bucket fits dominate -> frame-primary / retuned bucketing
    candidate
  - neither dominates -> batching-only uplift is weaker than hoped and the task
    should record that explicitly

### `M1` Targeted candidate implementation

- Land exactly one targeted batching change promoted by `M0`.
- Keep:
  - old greedy packer semantics everywhere outside the targeted intervention
  - global codec-frame budget `640`
  - no optimizer or runtime changes
- Do not mix multiple uplift ideas in the same code slice.

### `M2` Finite uplift proof on Hemma

- Launch the promoted `M1` candidate through the canonical detached
  `qwen-train launch` surface.
- Keep:
  - train/eval manifest family pairing aligned to the rebuilt bundle reality
  - `batch_size=8`
  - unchanged `640` global codec-frame budget
  - unchanged LR, optimizer, precision, and checkpoint policy
- Bound the proof at:
  - `max_steps=30`
  - `checkpoint_interval_steps=30`
- Accept only if:
  - the run stays finite through the bounded window
  - mean batch size beats the stable balanced baseline
  - singleton share beats the stable balanced baseline
  - steady-state train GPU median beats the stable balanced baseline

### `M3` Post-change ROCm attribution proof

- Only run this if `M2` yields a finite candidate worth attributing.
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
- The earlier local implementation slice added:
  - committed offline batch-plan analysis surface `qwen-batch-plan`
  - bounded quarantine candidate profile under the stable `640` cap
  - bounded quarantine plus upper-tail bucket candidate under the same cap
- The first offline replay precursor has already been executed against the rebuilt bundle:
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
- The revised `M0` is therefore now the fit-opportunity audit rather than
  another quarantine replay:
  - the prior quarantine hypothesis is falsified for this rebuilt bundle
  - there is no promoted occupancy candidate yet because the first replay
    produced only baseline-equivalent plans
  - launching a duplicate Hemma proof would not answer a new question
- The revised `M0` fit-opportunity audit has now been executed:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/verification/task-172-fit-audit-20260315a/20260315T004614Z`
  - profile:
    `hemma-throughput-balanced-v1`
  - codec-frame audit band:
    `320-375`
  - audited singleton count:
    `242`
  - same-bucket fit count:
    `55`
  - adjacent-lower-bucket fit count:
    `227`
  - same-bucket-only count:
    `0`
  - adjacent-lower-only count:
    `172`
  - both-fit count:
    `55`
  - neither-fit count:
    `15`
- That discriminator materially changes the next recommended change:
  - adjacent-lower-bucket opportunities dominate
  - same-bucket-only opportunities do not dominate at all
  - so the next promoted `M1` candidate should target the bucket signal /
    boundaries rather than a same-bucket lookahead policy
- The promoted `M1` implementation direction is now explicit:
  - add `hemma-throughput-balanced-frame-primary-v1`
  - keep the old greedy one-open-batch packer
  - keep the global codec-frame cap at `640`
  - switch only the bucket signal from combined sequence cost to
    codec-frame-count bucketing
  - reuse a narrower boundary ladder aligned to the active frame-limited regime
- The local `M1` implementation is now landed and covered by focused tests:
  - throughput profiles now expose an explicit `bucket_signal_kind`
  - the live sampler now buckets by the active policy signal rather than
    always using combined sequence cost
  - the offline fit-opportunity audit now uses the same active signal logic
  - focused batching tests now prove the frame-primary candidate changes the
    planned grouping while preserving the stable greedy packer semantics
- The promoted `M1` frame-primary candidate has now been compared offline on
  Hemma against the rebuilt bundle:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/verification/task-172-batch-plan-analysis-20260315b-frame-primary/20260315T010121Z`
  - compared profiles:
    - `hemma-throughput-balanced-v1`
    - `hemma-throughput-balanced-frame-primary-v1`
  - the frame-primary candidate is not an uplift:
    - baseline mean batch size:
      `1.4065934065934067`
    - frame-primary mean batch size:
      `1.4027397260273973`
    - baseline singleton share:
      `0.6675824175824175`
    - frame-primary singleton share:
      `0.6684931506849315`
    - baseline two-row share:
      `0.2857142857142857`
    - frame-primary two-row share:
      `0.2876712328767123`
  - the candidate does change grouping, but not in a way that improves the
    stable occupancy envelope
  - so `M2` is intentionally not launched for this candidate

## Deliverables

- [x] Bucketed non-`batch_size=1` throughput profile(s) implemented.
- [x] Vectorized/fused codebook path replaces the current fragmented loop.
- [x] Destabilizing best-fit packer reverted after Hemma isolation proved it
  breaks the stable balanced lane.
- [x] Committed offline batch-plan analysis surface exists for `M0`.
- [ ] One evidence-backed smaller uplift candidate chosen from the revised `M0`.
- [x] One bounded quarantine replay precursor was completed and explicitly rejected as a no-op
  for the initial quarantine threshold.
- [x] The revised `M0` fit-opportunity audit completed and selected bucket-signal
  retuning as the next promoted `M1` direction.
- [x] One targeted `M1` batching change implemented from the revised `M0`.
- [ ] One finite `M2` Hemma uplift proof completed or rejected with evidence.
- [ ] One evidence-backed default profile chosen for follow-on saturation runs.

## Acceptance Criteria

- [ ] The revised `M0` produces a committed fit-opportunity audit for singleton
  rows in the `320-375` codec-frame band.
- [x] The revised `M0` explicitly distinguishes same-bucket ordering misses from
  adjacent-lower-bucket grouping misses on the rebuilt bundle.
- [x] If the quarantine replay precursor produces only baseline-equivalent
  plans, the task records that null result explicitly and does not launch a
  duplicate Hemma proof.
- [ ] `M1` lands exactly one targeted batching change promoted by the revised `M0`.
- [x] `M1` lands exactly one targeted batching change promoted by the revised `M0`.
- [x] If the promoted `M1` candidate is baseline-equivalent or worse in offline
  replay, the task records that null result explicitly and does not launch `M2`.
- [ ] `M2` launches exactly one promoted `M1` candidate and records whether it
  stays finite through `30` optimizer steps / first durable checkpoint.
- [ ] If `M2` stays finite, bounded Hemma evidence shows higher steady-state
  train median GPU busy and better realized occupancy than the stable balanced
  baseline.
- [ ] If `M2` stays finite, `M3` records whether ROCm launch/sync overhead
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
- [ ] `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.cli.ml.qwen_batch_plan --pilot-bundle-root <rebuilt_bundle_root> --fit-audit-codec-frame-band-min 320 --fit-audit-codec-frame-band-max 375`
- [ ] `pdm run run-hemma -- pdm run qwen-train launch ...` for the promoted `M1` candidate
- [ ] If `M2` stays finite, one bounded ROCm attribution proof written under
  `build/verification/`.

## Checklist

- [x] Implementation complete
- [ ] Validation complete
- [x] Docs updated
