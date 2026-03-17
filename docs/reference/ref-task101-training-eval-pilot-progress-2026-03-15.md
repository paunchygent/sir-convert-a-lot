---
type: reference
id: REF-task101-training-eval-pilot-progress-2026-03-15
title: Task 101 Training/Eval Pilot Progress Ledger (2026-03-15)
status: active
created: 2026-03-15
updated: 2026-03-17
owners:
  - platform
tags:
  - qwen
  - hemma
  - task101
  - checkpoint-recovery
  - eval
  - training
links:
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-195-land-an-explicit-task-101-text-embedding-mask-policy-and-text-span-only-mitigation.md
  - docs/backlog/tasks/task-196-make-task-101-gradient-accumulation-runtime-configurable-for-bounded-proof-runs.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-182-add-standalone-eval-and-scheduled-train-stop-resume-control-for-task-101-qwen-training.md
  - docs/backlog/tasks/task-183-control-checkpoint-cadence-and-retention-for-scheduled-task-101-qwen-training.md
  - docs/backlog/tasks/task-185-backport-legacy-qwen-resume-compatibility-and-stale-bundle-override-for-task-101-checkpoint-recovery.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
---

## Purpose

Provide one canonical operator-facing ledger for the live Task 101
training/eval recovery lane after the scheduled-control posture shipped.

This document exists so operators do not have to reconstruct the current plan
from task notes, skill policy, or ad hoc Hemma terminal history. It records:

- the historical `1236` checkpoint baseline eval result
- the short diagnostic `1236 -> 1238` recovery probe and what it proved
- the currently approved strict resume target
- the exact artifact roots and commands that matter for the next live relaunch

## Current Operator Rule

For the preserved Task 101 legacy lane:

- treat `state-step-00001236` as the evaluated baseline checkpoint
- treat `state-step-00001238` as the canonical no-projection RCA checkpoint
  for the preserved Task 101 lane
- treat `state-step-00001406` from the bounded no-projection replay as the
  current canonical RCA checkpoint
- treat Story 29 / `T195-T199` as the explicit mitigation-and-restart gate for
  the preserved Task 101 lane
- do not resume from `1236` again unless a deliberate compatibility experiment
  requires it
- do not count the projection-enabled diagnostic experiments and the preserved
  no-projection lane as one continuous training series
- record future live training/eval progress here, not in the skill doc
- treat `T186` as the delivered optimizer-boundary remediation and proof slice
  that now informs `T193` and the next `T179` bounded-retry decision
- treat `T193` as the active numerical-stability slice that restores the
  upstream no-projection fine-tuning contract and adds clip-boundary stage
  forensics
- treat `T180` as the delivered first-pass truth/forensics slice
- treat Story 28 / `T187-T191` as the delivered permanent
  architecture-hardening lane; new control-plane or runtime logic must stay in
  the bounded `control_plane/`, `detached_runtime/`, `reporting/`, and
  focused `sft_12hz_*` runtime modules

Why this is now the clean plan:

- `1236` is the original high-water mark from the old launch and now has a
  real held-out eval baseline
- the short recovery probe already restored trainer state and wrote a newer
  durable checkpoint at `1238`
- that newer checkpoint carries a compatible saved cursor
  (`next_step_in_epoch=8`) for the current replacement bundle contract, so it
  avoids the confusing legacy cursor mismatch that existed at `1236`
- the projection-enabled replay and base restart both failed, which is
  evidence against injecting `text_projection` into the fine-tuning graph
  rather than evidence that the preserved no-projection lane is worthless
- the runtime now writes a `talker_runtime` fingerprint so future shape drift
  cannot hide behind silent fallback resolution
- the original legacy launch snapshot still carries stale checkpoint cadence
  settings (`2/100/2`), so the next strict resume must pass explicit control
  overrides rather than inheriting those stale values
- the clean `1401 -> 1406` replay crossed the old failure boundary without a
  new non-finite event, but the later bounded continuation still failed at
  `1417`, so `1406` is now treated as a reusable RCA checkpoint rather than a
  newly trusted continuation baseline
- the later bounded `1406 -> 1418` replay reproduced the `1417` failure and
  proved the first bad backward surface is `input_text_embedding.grad`, not
  clipping or `optimizer.step()`
- the same replay narrowed the leading structural cause to the active
  codec-span text-pad surface on the no-projection training graph, so the next
  accepted operator move is a bounded mitigation proof rather than another
  fresh training restart
- the next restart gate is now explicit:
  - preferred:
    - clear `1406 -> 1418`
    - then reach `1500`
    - then complete the scheduled eval at `1500`
  - fallback:
    - only after the structural mitigation and planned accumulation ablations
    - clear `1406 -> 1470`
    - then run standalone held-out eval from the `1470` checkpoint
  - after Story 30 Candidate 1 landed through `T207-T209`, the next governed
    proof owner is `T210`:
    - rerun the bounded `1406 -> 1470` gate on the semantic-only assembly
      code path
    - use accumulation `1`
    - then run detached standalone eval only if `1470` is truthful
    - if that governed proof still fails before `1470`, do not relaunch the
      same lane; do one short fresh-start discriminant proof first
  - `T210` then failed immediately at optimizer step `1407`, so Candidate 1 is
    now negative evidence as an inherited-state rescue lane from
    `state-step-00001406`
  - `T211` is now closed negative fresh-start evidence:
    - `task211-20260317t130740z-freshstart-a4` failed at optimizer step `1`
    - the first poisoned parameter surface was still
      `text_embedding.weight.grad`
    - pre-step parameters and optimizer state were finite
    - no checkpoint was minted and no eval claim was produced
    - replay-amassed inherited state is therefore no longer the leading
      explanation for the current failure family
  - `T212` is now closed positive discovery evidence:
    - the truthful probe run was
      `task212-20260317t141500z-lineage-a3`
    - all three branch orders failed on the row pair
    - both rows failed independently in isolation
    - the earliest instrumented non-finite backward hook appeared at
      `input_embeddings` after still-finite `hidden_states` and
      `talker_hidden_states` gradients
    - the targeted RCA still reported `input_text_embedding.grad` first and
      `text_embedding.weight.grad` as the first poisoned parameter surface
  - `T213` is now the next governed discovery owner:
    - truthful probe:
      `task213-20260317t143810z-talkercore-a1`
    - pair `main_loss` and `combined_loss` first localized at
      `talker_core.layer_16.post_attention_layernorm`
    - pair `sub_talker_loss` first localized at
      `talker_core.layer_15.output`
    - isolated row probes localized to `talker_core.layer_16.output` for
      `main_loss` / `combined_loss` and `talker_core.layer_15.output` for
      `sub_talker_loss`
    - pair-main finite gradient magnitudes exploded from `1.07e-4` at
      `layer_27.output` to `3.19e38` at `layer_16.output` before
      `layer_16.post_attention_layernorm` turned non-finite
    - Candidate `3` should not open yet because a smaller talker-core split is
      still yielding new signal
  - `T214` is now closed positive discovery evidence:
    - truthful proof:
      `task214-20260317t151800z-boundary-a1`
    - pair `main_loss` / `combined_loss` first localized at
      `talker_core.layer_16.mlp.gated_product`
    - those pair branches still had finite gradients at
      `layer_16.output` / `layer_16.mlp.down_proj`
      (`3.19e38` / `3.26e38`) before the first non-finite hook
    - pair `sub_talker_loss` first localized at `talker_core.layer_15.output`
    - isolated rows still failed independently at `layer_16.output` or
      `layer_15.output`
    - replay and text-span leakage are no longer the leading explanations for
      the current fresh-start failure family
  - Story 31 is now the active governed owner:
    - recover a stable fresh-start bundle-learning recipe through bounded
      talker-core stabilization
    - use an exploration-first lane:
      fast matrix iteration, compact result table, no proof package per cell
    - `T216` is now complete:
      - the first bounded stabilization variants are:
        `off`, `layer16_gated_fp32`, `layer16_gated_fp32_clamp_1e4`
      - the committed exploration surface is:
        `pdm run qwen-story31-stability-lab run`
      - it writes one compact matrix run under a single output root:
        `results.json`, `results.md`, and `variant-reports/<variant>.json`
    - `T215` is now complete:
      - the committed promotion surface is:
        `pdm run qwen-story31-stability-lab gate --output-root <lab-output-root>`
      - it consumes `results.json` and writes `gate.json` plus `gate.md`
      - baseline `off` must reproduce the exact pair-family seams from `T214`
      - candidate `layer16_gated_fp32` must keep those exact surfaces finite
    - the first real Story 31 Hemma matrix now records negative evidence:
      - output root:
        `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task215-20260317t160500z-a2`
      - baseline `off` reproduced the exact `T214` pair-family seams
      - candidate `layer16_gated_fp32` failed the promotion gate unchanged
      - `layer16_gated_fp32_clamp_1e4` also reproduced the same pair-family seams
    - `T218` is now complete as negative exploration evidence:
      - output root:
        `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task218-20260317t173122z-a1`
      - implemented variants:
        - `layer16_gated_fp32_rescale_1e3_layer15_out_0p5`
        - `layer16_gated_fp32_rescale_1e2_layer15_out_0p25`
      - baseline `off` still reproduced the exact `T214` pair-family seams
      - both new variants changed the pair-family neighborhood, but neither
        candidate kept the exact target seams finite
      - both promotion gate runs recorded:
        - `exact_family_reproduced_by_baseline=true`
        - `candidate_exact_surfaces_finite=false`
        - `promotion_passed=false`
    - `T219` is now the active next exploration slice:
      - keep the moderate T218 posture as the preferred base ingredient
      - target the shifted `layer_16.output` /
        `layer_16.input_layernorm` handoff neighborhood
      - keep explicit visibility on the surviving
        `sub_talker_loss` `layer_16.mlp.gated_product` fallback
    - `T217` runs the first short fresh-start Hemma proof only for the first
      promoted winner
    - do not reopen replay framing while this solution lane is active

## Active Artifact Roots

- Canonical run root:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z`
- Canonical legacy launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot/task101-20260313t102144z`
- Replacement bundle root for current recovery:
  `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1`
- Held-out eval manifest:
  `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1/manifests/swedish_checkpoint_dev.prepared.jsonl`
- Current strict resume checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00001238`
- Exact diagnostic capture checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-capture1401-a3/diagnostic-state/checkpoints/state-step-00001401`
- Current canonical RCA checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`
- Latest checkpoint pointer:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/latest_checkpoint.json`

## Timeline

### 2026-03-15: Standalone Eval Baseline

- Command surface: `pdm run qwen-train eval`
- Checkpoint evaluated:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00001236`
- Eval output root:
  `/srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot/task101-20260313t102144z/evals/eval-20260315T104201Z`
- Result:
  - `eval_loss=6.440637648105621`
  - `eval_batches_completed=8`
  - `status=completed`

Interpretation:

- this is the canonical pre-resume held-out baseline for the preserved legacy
  lane
- future training/eval comparisons should treat this as the “before resume”
  reference point

### 2026-03-15: Diagnostic Recovery Probe

- Source checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00001236`
- Diagnostic resumed launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T102149Z`
- Result:
  - trainer state restored successfully
  - one newer durable checkpoint written at optimizer step `1238`
  - probe then stopped intentionally

What this probe proved:

- the legacy launch metadata can now be loaded without manual edits
- `--pilot-bundle-root` override works for stale source metadata
- stale pre-resume `report.json` is now hidden correctly during detached
  inspection

What this probe does not count as:

- not acceptance evidence for the ongoing pilot
- not the baseline eval result
- not a reason to keep resuming from `1236` when `1238` already exists

### 2026-03-15: Canonical Strict Resume Relaunch

- Relaunch command used:

```bash
pdm run run-hemma -- pdm run qwen-train resume \
  --launch-root /srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot/task101-20260313t102144z \
  --pilot-bundle-root /srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1 \
  --checkpoint-interval-steps 500 \
  --eval-interval-steps 100 \
  --durable-checkpoint-retention 3 \
  --skip-build
```

- New detached launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T110545Z`
- New container:
  `qwen-train-20260315T110545Z`
- Relaunch source checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00001238`

Truth confirmed from detached status at `2026-03-15T11:09:57Z`:

- `status=running`
- `checkpoint_interval_steps=500`
- `eval_interval_steps=100`
- `durable_checkpoint_retention=3`
- `current_optimizer_step=1268`
- `latest_loss=6.697592735290527`
- `smoothed_loss=6.445340894588681`

Interpretation:

- the active lane is no longer carrying forward the stale legacy
  `2/100/2` posture
- operators can now read launch/status artifacts and see the truthful
  scheduled-control contract from the start of the resumed lane
- the preserved legacy checkpoint has advanced beyond `1238` without requiring
  manual launch JSON edits or a cursor-reset workaround

### 2026-03-15: Strict `1238` Relaunch Failure

- Failed detached launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T110545Z`
- Failure status checked at:
  `2026-03-15T12:18:25Z`
- Terminal failure:
  - `NonFiniteLossError`
  - `optimizer_step=1358`
  - `current_train_iteration=616`
  - `current_epoch=4`
  - `consecutive_non_finite_steps=3`
- Held-out eval truth preserved from the same lane:
  - `latest_eval_loss=6.574727833271027`
  - `best_eval_loss=6.574727833271027`
  - `best_eval_step=1300`
  - `eval_runs_completed=1`
- Durable checkpoint truth:
  - `latest_checkpoint.json` still points to
    `state-step-00001238`
  - no newer durable trainer-state checkpoint finalized before failure

Important operator interpretation:

- `current_epoch=4` is the trainer's zero-based resumed epoch cursor, not proof
  that this relaunch began from a fresh human-facing "epoch 1"
- the resumed `1238` durable checkpoint already carried `next_epoch=1` and
  `next_step_in_epoch=8`, so the relaunched lane was already inside a later
  resumed epoch window
- the live `phase_history` entries at optimizer steps `1300` and `1332` used
  the generic phase label `checkpoint-save`, but that label currently conflates
  durable trainer-state saves with export-only epoch/final checkpoint saves
- because `latest_checkpoint.json` never advanced beyond `1238`, operators
  should not assume those later `checkpoint-save` entries represent durable
  recovery points

Remediation owners for this failure:

- `docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md`
  delivered:
  - bounded forensic instrumentation for the combined loss, main talker loss,
    sub-talker loss, and gradient norm
  - per-microbatch row provenance and ordered tensor-finiteness probes so the
    next `NaN` shows the exact rows and tensor families behind optimizer steps
    like `1356-1358`
  - explicit sampler-randomness governance instead of hidden global
    `random.shuffle(...)` behavior
  - truthful durable-versus-export checkpoint phase labels
  - explicit epoch-semantics reporting in status/report artifacts
- `docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md`
  now owns:
  - deterministic detached replay for the `1238 -> 1405/1406` failure window
  - targeted text-embedding / text-projection parameter probes
  - targeted optimizer-state probes for those params
  - the fail-closed guard that must stop the lane before a corrupt update is
    applied

### 2026-03-15: Deterministic Replay Pivot

The approved plan is no longer “keep rerunning the full resumed lane and learn
one small thing each time.”

The canonical next root-cause workflow is:

1. `pdm run qwen-train diagnose-non-finite`
1. inspect the bounded detached diagnostic report
1. land the targeted optimizer-boundary fix
1. rerun the same detached diagnostic surface
1. only then decide whether `T179` can retry a bounded stability proof

### 2026-03-15: Instrumented Replay Evidence

- Instrumented replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T134652Z`
- Terminal failure:
  - `NonFiniteLossError`
  - `optimizer_step=1408`
  - first pre-corruption boundary at `optimizer_step=1405`
- What the replay proved:
  - step `1405` still had finite forward losses but already had non-finite
    `grad_norm`
  - the loop then allowed `optimizer.step()` to execute
  - step `1406` entered with `input_text_embedding` already poisoned, which
    then propagated through the rest of the forward path
  - the later `1406-1408` rows are therefore victims of post-update weight
    corruption, not the original trigger
- Operator conclusion:
  - this is an optimizer-boundary corruption bug, not just a status/reporting
    bug and not just a guessed bad-row issue
  - the next accepted proof must show the guarded lane stops before
    `optimizer.step()` is attempted

### 2026-03-15: Guarded Detached Proof Completed

- Canonical guarded proof launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T180643Z`
- Source launch root reused for truthful control settings:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T110545Z`
- Relaunch source checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00001238`
- Why the earlier detached attempt was discarded:
  - the legacy source launch metadata still carried stale `2/100/2`
    checkpoint controls, so it spent the lane in misleading
    `durable-checkpoint-save` churn instead of proving the guarded boundary
- Machine-readable agreement across `status.json`, `report.json`, and
  `diagnostic_replay_bundle.json`:
  - `status=failed`
  - `current_optimizer_step=1405`
  - `trigger_reason=pre_step_non_finite_grad_norm`
  - `first_non_finite_surface=grad_norm`
  - `optimizer_step_attempted=false`
  - `optimizer_step_completed=false`
- Pre-step probe truth at the guarded boundary:
  - `text_embedding.weight` parameters remained finite
  - `text_embedding.weight.grad` was already non-finite
  - optimizer state for `text_embedding.weight` (`step`, `exp_avg`,
    `exp_avg_sq`) remained finite
- Operator conclusion:
  - the lane now fails closed at optimizer step `1405` before applying the
    corrupt update
  - `T186` is complete as the required proof slice for the next bounded `T179`
    decision

### 2026-03-15: Projection-Enabled Replay Fails Earlier At `1239`

- Projection-enabled replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task179-20260315t-textpath-replay-a1`
- Status checked at:
  `2026-03-15T19:36:45Z`
- Diagnostic metadata still requested:
  - `start_optimizer_step=1405`
  - `end_optimizer_step=1406`
- Actual failure truth from `status.json` / `report.json`:
  - `status=failed`
  - `trigger_reason=pre_step_non_finite_grad_norm`
  - `current_optimizer_step=1239`
  - `current_train_iteration=140`
  - `optimizer_step_attempted=false`
  - `optimizer_step_completed=false`
- Diagnostic targeted text-path family:
  - `text_embedding.weight`
  - `text_projection.linear_fc1.weight`
  - `text_projection.linear_fc1.bias`
  - `text_projection.linear_fc2.weight`
  - `text_projection.linear_fc2.bias`
- Pre-step truth at the projection-enabled boundary:
  - forward losses remained finite
  - all probed text-path parameters remained finite
  - probed optimizer state remained finite
  - `text_embedding.weight.grad` and all probed `text_projection.*` gradients
    were already `NaN`
- Operator conclusion:
  - the talker-runtime alignment fix was necessary because it removed the old
    projection blind spot and proved the projection-enabled experiment was
    actually running
  - the fix was not sufficient to make the resumed lane stable
  - the current diagnostic surface did not skip directly to the old `1405`
    window in practice; it exposed an earlier projection-enabled boundary at
    `1239`

### 2026-03-15: Runtime Fingerprint Hardening Landed

- The shared talker resolver now emits a machine-readable runtime fingerprint
  covering:
  - resolved text-embedding path
  - resolved codec-embedding path
  - resolved text-projection path
  - whether each resolved surface is probeable as an `nn.Module`
- The in-container trainer persists that payload into:
  - `talker_runtime.json`
  - live `status.json`
  - terminal `report.json` / `training_summary`
- Focused resolver-matrix tests now cover:
  - talker-level projection present
  - nested `model.talker.model.text_projection` fallback
  - no projection present
  - callable-but-non-module projection present
- Operator conclusion:
  - future runtime-shape drift should now be visible immediately in artifacts
    rather than inferred indirectly from missing guard probes

### 2026-03-15: Projection-Enabled Base Restart Failed At Step `1`

- Projection-enabled restart launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task101-20260315t-clean-restart-a1`
- Failure truth:
  - clean base weights still failed before `optimizer.step()`
  - the first optimizer boundary was already non-finite at step `1`
  - forward losses remained finite while gradients across the projection-enabled
    text path were already `NaN`
- Operator conclusion:
  - this is evidence against injecting `text_projection` into the fine-tuning
    graph
  - it is not evidence that the preserved Task 101 no-projection lane is
    worthless
  - the projection-enabled replay and restart are now classified as diagnostic
    experiments, not as the new canonical lane

### 2026-03-15: No-Projection Contract Restored Locally

- `T193` now owns the active numerical-stability slice:
  - train and eval were restored to the upstream no-projection fine-tuning
    contract
  - `talker_runtime` still fingerprints the projection surface when present,
    but the fine-tuning forward graph no longer injects it
  - optimizer-boundary artifacts now distinguish:
    - `pre_clip`
    - `clip_grad_norm`
    - `post_clip`
    - `post_step`
- Operator conclusion:
  - `state-step-00001238` remains the canonical no-projection RCA checkpoint
  - the next bounded live proof should mint a fresh diagnostic checkpoint near
    optimizer step `1401` and replay `1401 -> 1406` with the new stage
    probes

### 2026-03-15: Resume Reached `1405`, But The Planned `1401` Checkpoint Was Missed

- Resume launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task193-20260315t-pre1401-resume-a1`
- Source checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00001238`
- What happened:
  - the restored no-projection lane resumed cleanly and advanced through
    optimizer step `1400`
  - the operator plan was to stop near `1401` to mint a fresh durable
    checkpoint before the known failure band
  - that stop never happened, and the lane was allowed to continue into the
    known failing boundary at optimizer step `1405`
- Failure truth at `1405`:
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - forward losses were still finite
  - pre-step parameters and optimizer state were still finite
- Operator failure:
  - this was a monitoring and control failure, not a model-side surprise
  - the run was watched manually with coarse sleep-based polling even though
    the lane was paying for real eval and export-checkpoint phases on the way
    to the stop window
  - that timing assumption was catastrophically wrong for a near-boundary
    checkpoint mint and caused the planned `1401` checkpoint to be missed
- Avoidance rule:
  - do not rely on manual sleep-based timing when the goal is a checkpoint
    just ahead of a known failure boundary
  - the next checkpoint-minting attempt must use an explicit automated stop
    threshold tied to `current_optimizer_step`, with the stop request issued
    before the target boundary is reached
  - specifically, use a committed polling/stop surface that requests the stop
    at or before `1398-1400`; do not wait for `1401` to appear in a human
    status check
- Consequence:
  - no fresh durable checkpoint was minted; `latest_checkpoint.json` still
    points to `state-step-00001238`
  - despite that operator failure, the resumed lane still produced the
    stage-resolved RCA truth we needed: the first non-finite event is
    `pre_clip`, not `clip_grad_norm`, `post_clip`, or `optimizer.step()`

### 2026-03-15: Story 28 Delivered

The permanent architecture-hardening lane is no longer future work.

- `qwen_train.py` is now a composition root
- host-side orchestration is split across
  `ml/qwen/training/control_plane/`
- detached launch/inspect/stop behavior is split across
  `ml/qwen/training/detached_runtime/`
- reporting is split across `ml/qwen/training/reporting/`
- the patched training runtime is reduced to orchestration plus bounded
  `sft_12hz_*` runtime modules
- `orchestrator.py` and `reporting.py` are deleted and must not return
- `RULE-095` and architecture guard tests now enforce the split

### 2026-03-15: Abandoned Artifact Cleanup

Removed after the March 15 relaunch candidate was superseded by later proof
work:

- exited containers:
  - `qwen-train-20260315T095620Z`
  - `qwen-train-20260315T102149Z`
  - `qwen-train-20260315T105831Z`
  - `qwen-train-20260315T083102Z`
- abandoned verification roots:
  - `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T095620Z`
  - `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T102149Z`
  - `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T105831Z`
- stale detached resource-monitor workers that kept recreating those abandoned
  roots

Post-cleanup Hemma check:

- only active Qwen training container:
  `qwen-train-20260315T110545Z`
- `/srv/scratch` free space:
  about `99GB`

### 2026-03-16: Exact `1401` Capture Succeeded

- Capture launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-capture1401-a3`
- Captured checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-capture1401-a3/diagnostic-state/checkpoints/state-step-00001401`
- Result:
  - in-trainer exact capture completed at optimizer step `1401`
  - the run exited cleanly without overshooting into the old `1405` failure
    window
  - `diagnostic_state_capture.json` was written successfully

Operator conclusion:

- trainer-native exact capture is now the canonical way to mint a
  near-boundary checkpoint
- external polling/stop control is no longer the approved method for a
  narrow optimizer-step boundary

### 2026-03-16: Bounded `1401 -> 1406` Replay Crossed The Old Failure Window Cleanly

- Replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1`
- Source checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-capture1401-a3/diagnostic-state/checkpoints/state-step-00001401`
- Diagnostic-window artifact:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/diagnostic-window/optimizer-step-00001405.json`
- Result:
  - the replay completed successfully through optimizer step `1406`
  - `optimizer-step-00001405.json` reported:
    - `first_non_finite_stage = null`
    - `first_non_finite_tensor = null`
  - the old `801-804` microbatch window stayed finite in this replay
  - a new durable checkpoint was minted at:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`

Operator conclusion:

- the exact `1401` checkpoint cleared the old `1405` boundary
- `state-step-00001406` is now the right reusable checkpoint for the next RCA
  slice
- crossing `1405` once did not prove the lane is stable; it only proved that
  the old `1405` failure was not deterministic from the exact `1401`
  checkpoint

### 2026-03-16: Bounded `1406` Continuation Failed Again At `1417`

- Continuation launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task101-20260316t-5pass-pilot-a1`
- Source checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`
- Failure checked at:
  `2026-03-16T10:13:03Z`
- Terminal truth:
  - `status=failed`
  - `current_optimizer_step=1417`
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - `optimizer_step_attempted=false`
  - `optimizer_step_completed=false`
- Probe truth:
  - forward losses stayed finite
  - parameters stayed finite
  - optimizer state stayed finite
  - `text_embedding.weight.grad` had `190464` `NaN` elements
    (`93` full embedding rows at width `2048`)
- Failing accumulated microbatch window:
  - train iteration `849`:
    manifest line `39`
  - train iteration `850`:
    manifest line `31`
  - train iteration `851`:
    manifest line `101`
  - train iteration `852`:
    manifest line `20`

Operator conclusion:

- the lane is still numerically unstable
- the instability is not tied only to the old `1405` window
- `1406` must be treated as the canonical RCA checkpoint again, not as a
  trusted pilot-continuation baseline
- the next accepted operator move is a bounded RCA replay from `1406` over the
  `1417` window, not another continuation attempt

### 2026-03-16: Bounded `1406 -> 1418` Replay Reproduced `1417` And Narrowed The Cause

- Replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1417-rca-a1`
- Source checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`
- Replay result checked at:
  `2026-03-16T10:36:50Z`
- Terminal truth:
  - `status=failed`
  - `current_optimizer_step=1417`
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - `optimizer_step_attempted=false`
  - `optimizer_step_completed=false`
- New bounded-replay RCA truth:
  - `step_forensics.first_non_finite_gradient_surface=input_text_embedding.grad`
  - `step_forensics.first_non_finite_gradient_train_iteration=851`
  - `step_forensics.first_non_finite_train_iteration=852`
  - microbatches `849` and `850` stayed clean
  - microbatch `851` was the first poisoned sample
  - microbatch `852` inherited the already-poisoned accumulated parameter
    gradient at the sync boundary
- Per-sample RCA truth for microbatch `851`:
  - `507` of `508` token positions were non-finite in
    `input_text_embedding.grad`
  - the single finite token position was the final position, which aligns with
    the train-step `inputs_embeds[:, :-1, :]` slice excluding the terminal
    token from the active forward path
  - the failing sample had `93` unique token ids
  - the poisoned `text_embedding.weight.grad` had `93` non-finite rows
  - those `93` rows matched the sample's `93` unique token ids exactly
  - token id `151671` appeared `375` times in the failing sample
- Structural interpretation:
  - the replay proves a sequence-level backward blow-up on the active
    text-embedding path, not an isolated one-token failure
  - the repeated token `151671` is the dominant repeated text-channel filler in
    the failing sample; that aligns with the Qwen batch contract writing
    `tts_pad_token_id` across the codec span while keeping
    `text_embedding_mask` active through `8 + text_ids_len + codec_ids_len`
  - the public upstream Qwen `finetuning/dataset.py` uses the same active
    codec-span text-pad pattern, so this is an upstream-compatible instability
    surface rather than a repo-local projection mismatch

Operator conclusion:

- `1406` remains the canonical reusable RCA checkpoint
- the instability is now narrowed to a sequence-level backward blow-up on the
  active text-embedding path, with codec-span text-pad amplification as the
  leading structural cause
- the next accepted operator move is not another continuation or restart
- the next accepted operator move is one bounded mitigation proof from `1406`
  that removes or detaches the codec-span text-pad surface and replays the
  `1417` window
- `T195` has now landed that first structural mitigation surface:
  - `text_embedding_mask_policy` is an explicit runtime/control-plane contract
  - supported values are `legacy_codec_span` and `text_span_only`
  - fresh `qwen-train launch` runs now default to `text_span_only`
  - older launch metadata still rehydrates as `legacy_codec_span` unless
    operators explicitly override it
  - runtime fingerprint, launch metadata, standalone eval artifacts, and
    machine-readable reporting now surface the active policy

## Superseded Operator Plan

The abandoned plan is:

- “run standalone eval on `1236`, then resume from `1236` again”
- “promote the projection-enabled replay/restart as the authoritative new
  mainline”

That plan is now superseded because:

- the probe already minted `1238`
- `1238` preserves more training progress
- `1238` has a truthful compatible cursor for the replacement bundle
- rolling back to `1236` would spend operator time for no gain
- after the strict `1238` relaunch failed at `1358`, the later
  instrumented replay failed at `1408`, and the guarded diagnostic then failed
  closed at `1405`, the next move is no longer "resume immediately again"; it
  is "use the completed `T186` proof to decide the next bounded `T179` retry"
- after the projection-enabled replay failed even earlier at `1239` and the
  projection-enabled base restart failed at step `1`, the next move is no
  longer "promote the projection-enabled graph"; it is "restore the upstream
  no-projection contract and debug the preserved lane with better stage
  forensics"

## Canonical Next Step

Do not relaunch the projection-enabled training experiment.
Do not launch another fresh Task 101 training continuation or restart yet.

The next canonical action is a bounded no-projection mitigation proof from
`state-step-00001406`:

1. reuse `state-step-00001406` as the canonical RCA checkpoint
1. narrow the active `text_embedding_mask` to the true text span only, or
   equivalently zero/detach the codec-span text-pad positions
1. rerun only the bounded `1406 -> 1418` replay window
1. treat reduced `gradient_accumulation_steps` as the secondary ablation if the
   mask-only mitigation does not remove the instability
1. prefer proving the mitigated lane all the way to step `1500` and completing
   the scheduled eval there before allowing the next clean restart
1. if `1500` still fails after the structural fix and planned accumulation
   ablations, use the fallback gate:
   - clear `1406 -> 1470`
   - mint the `1470` checkpoint
   - run standalone held-out eval from that checkpoint

### 2026-03-16: Story 29 Created To Gate The Next Clean Restart

- New story:
  `docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md`
- New tasks:
  - `T195` explicit `text_embedding_mask_policy` with `legacy_codec_span` and
    `text_span_only`
  - `T196` runtime-configurable `gradient_accumulation_steps`
  - `T197` preferred bounded proof through `1406 -> 1418` and then to `1500`
    with scheduled eval
  - `T198` conditional accumulation ablation and fallback
    `1470 + standalone eval` gate
  - `T199` first clean base restart after a proof gate passes

Why this matters:

- the repo now has a single canonical RCA checkpoint for cheap bounded proofs:
  `state-step-00001406`
- the RCA already identifies the leading structural amplifier:
  codec-span text-pad activation on the no-projection training graph
- the story makes the restart gate explicit instead of leaving it implied by
  ad hoc operator judgment
- the training reference ledger is now the mandatory place to record whether
  the preferred `1500` gate or the fallback `1470 + standalone eval` gate
  justified the next clean restart

### 2026-03-16: `T195` Landed The Explicit Text-Embedding Mask Policy

- Delivered task:
  `docs/backlog/tasks/task-195-land-an-explicit-task-101-text-embedding-mask-policy-and-text-span-only-mitigation.md`
- Runtime/control-plane contract:
  - `legacy_codec_span`
  - `text_span_only`
- Launch/control truth:
  - fresh `qwen-train launch` defaults to `text_span_only`
  - `resume`, `capture-diagnostic-state`, `diagnose-non-finite`, standalone
    eval, and schedule flows accept explicit overrides while keeping older
    launch metadata compatible through `legacy_codec_span`
- Artifact truth:
  - dataset collation now computes the active text-embedding span from the
    explicit policy rather than a hard-coded codec-span assumption
  - `talker_runtime` fingerprints now record the active
    `text_embedding_mask_policy`
  - detached launch metadata, training status/report payloads, replay bundle
    settings, and standalone eval artifacts now surface the same policy
- Validation truth:
  - focused tests proved `legacy_codec_span` preserves the old active span
  - focused tests proved `text_span_only` narrows the active text-embedding
    surface to the true text span only

Operator conclusion:

- the first structural mitigation surface is now committed and visible
- `legacy_codec_span` is now a bounded RCA reproduction mode only; it is not
  allowed to silently ride along into the future restart lane
- the next implementation step is `T196`, so the same bounded proof lane can
  compare accumulation `4`, `2`, and `1` without code edits
- the next Hemma proof must use the explicit Story 29 contract rather than any
  implicit batch-mask behavior

### 2026-03-16: `T196` Landed Runtime-Configurable Gradient Accumulation

- Delivered task:
  `docs/backlog/tasks/task-196-make-task-101-gradient-accumulation-runtime-configurable-for-bounded-proof-runs.md`
- Runtime/control-plane contract:
  - supported values are `1`, `2`, and `4`
  - canonical default remains `4`
- Control-plane truth:
  - `launch`, `resume`, `capture-diagnostic-state`, `diagnose-non-finite`,
    `eval`, and `schedule` now all accept
    `--gradient-accumulation-steps`
- Artifact truth:
  - detached launch metadata now snapshots the effective accumulation value
  - in-container trainer and standalone evaluator entrypoints both receive the
    same explicit setting
  - status/report payloads, step semantics, standalone eval artifacts, replay
    bundles, and schedule control math now surface the effective value
- Validation truth:
  - focused tests passed across launch/control-plane parsing, detached command
    building, standalone eval orchestration, schedule targeting, diagnostic
    replay, capture flow, and train-loop reporting

Operator conclusion:

- the bounded proof lane no longer needs code edits to compare accumulation
  `4`, `2`, and `1`
- reduced accumulation remains the secondary ablation only; the first proof is
  still `text_span_only` with accumulation `4`
- if Story 29 proves `text_span_only` as part of the winning mitigation,
  `legacy_codec_span` must be removed before `T199` launches the next clean
  restart

### 2026-03-16: `T203` Closed By Reverting The Auxiliary Codebook Fusion Helper

- Delivered task:
  `docs/backlog/tasks/task-203-audit-the-auxiliary-codebook-fusion-hot-path-against-story-29-mixed-precision-and-proof-lane-contracts.md`
- Hemma proof surfaces used:
  - `pdm run run-hemma -- pdm run qwen-codebook-fusion-proof-detached launch`
  - `pdm run run-hemma -- pdm run qwen-codebook-fusion-proof-detached status`
- Proof artifact root:
  - `build/verification/qwen-codebook-fusion-proof/`
- Hemma runtime truth:
  - repo `HEAD` on Hemma was `5f421072e89bb5517210dd46b237f70900f2eab7`
  - the detached proof completed with ROCm available and the governed Qwen
    image rebuilt successfully
- Numeric/runtime result:
  - `bf16`: worst max error stayed `0.0625`, while runtime rose from about
    `0.492ms` to about `0.620ms`
  - `fp16`: worst max error stayed `0.0078125`, while runtime rose from about
    `0.492ms` to about `0.619ms`
- Decision:
  - revert the explicit `float32` auxiliary-codebook reducer from the Story 29
    proof lane and keep the plain vectorized reduction
- Operator conclusion:
  - the auxiliary codebook helper is not the winning Task 101 mitigation and
    must not be treated as part of the restart-gating proof lane
  - `T197` is now the next canonical step from `state-step-00001406`

### 2026-03-16: `T197` Hemma Proof Failed Again At `1417` Under `text_span_only`

- Delivered task:
  `docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md`
- Proof id:
  `task197-20260316t183555z-a1`
- Local proof artifact root:
  `build/verification/qwen-t197-proof/task197-20260316t183555z-a1/`
- Remote replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task197-20260316t183555z-a1-window`
- Runtime truth:
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=4`
  - the replay reused the canonical RCA checkpoint `state-step-00001406`
- Replay result:
  - detached replay exited with `exit_code=1`
  - `current_optimizer_step=1417`
  - `current_train_iteration=852`
  - the preferred `1500` continuation did not launch
- Failure truth:
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - the first bad backward surface remained `input_text_embedding.grad`
  - the replay preserved the same step-`1417` failure shape as the earlier
    bounded RCA lane
- Operator conclusion:
  - `text_span_only` alone is not sufficient to clear the preferred Story 29
    gate
  - `T198` is now the next active task for the planned accumulation ablations
  - the next clean restart remains blocked

## 2026-03-16: T198 Accumulation-2 Cleared 1417 But Hit Scratch-Capacity Failure

- Delivered task:
  `docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md`
- Proof id:
  `task198-20260316t185616z-accum2-a1`
- Local proof artifact root:
  `build/verification/qwen-t198-proof/task198-20260316t185616z-accum2-a1/`
- Remote replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task198-20260316t185616z-accum2-a1-window`
- Runtime truth:
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=2`
  - the replay reused the canonical RCA checkpoint `state-step-00001406`
- Replay result:
  - detached replay exited with `exit_code=1`
  - `current_optimizer_step=1418`
  - the replay did not fail on a non-finite gradient
  - the `1500` continuation did not launch
- Failure truth:
  - the terminal blocker was storage, not the old `1417` numerical failure
  - the durable checkpoint save refused to proceed because Hemma scratch free
    space was about `9 GB` while the save guard required about `30 GB`
- Operator conclusion:
  - accumulation `2` is positive numerical evidence because it cleared the old
    `1417` failure window
  - the preferred gate is still incomplete because the replay did not exit
    cleanly
  - `T204` is now the active enabling task:
    restore scratch headroom, archive cold artifact trees onto storage with
    symlink-backed path stability, and make future Story 29 proof launches
    fail early on insufficient headroom

## 2026-03-16: T198 Clean Rerun Cleared 1418 But The Preferred 1500 Gate Failed At 1428

- Delivered tasks:
  - `docs/backlog/tasks/task-204-restore-story-29-scratch-headroom-and-establish-cold-artifact-demotion-policy-on-hemma.md`
  - `docs/backlog/tasks/task-205-establish-idle-safe-recurring-hemma-scratch-maintenance.md`
  - `docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md`
- Proof id:
  `task198-20260316t202541z-accum2-a2`
- Local proof artifact root:
  `build/verification/qwen-t198-proof/task198-20260316t202541z-accum2-a2/`
- Remote replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task198-20260316t202541z-accum2-a2-window`
- Remote preferred-gate launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task198-20260316t202541z-accum2-a2-gate1500`
- Runtime truth:
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=2`
  - the rerun reused the canonical RCA checkpoint `state-step-00001406`
- Bounded replay result:
  - the detached `1406 -> 1418` replay exited cleanly with `exit_code=0`
  - `current_optimizer_step=1418`
  - one scheduled eval completed at that replay boundary
  - the replay minted
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task198-20260316t202541z-accum2-a2-window/diagnostic-run/checkpoints/state-step-00001418`
- Preferred `1500` continuation result:
  - the continuation launched from that clean `1418` checkpoint
  - the detached continuation exited with `exit_code=1`
  - `current_optimizer_step=1428`
  - `current_train_iteration=852`
  - no newer durable checkpoint beyond `1418` was minted
- Failure truth:
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - `optimizer_step_attempted=false`
  - parameters and optimizer state probes remained finite before the attempted
    optimizer step
- Operator conclusion:
  - accumulation `2` is strong positive evidence for clearing the old `1417`
    boundary
  - accumulation `2` is still negative preferred-gate evidence because the
    continuation failed before `1500`
  - the next clean restart remains blocked
  - the next operator move must now be chosen explicitly:
    - either the documented fallback `1406 -> 1470` plus standalone eval gate
    - or the next accumulation ablation lane if that is judged more valuable

## 2026-03-16: T198 Accumulation-1 Cleared 1418 But The Preferred 1500 Gate Failed At 1449

- Delivered task:
  `docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md`
- Proof id:
  `task198-20260316t213409z-accum1-a1`
- Local proof artifact root:
  `build/verification/qwen-t198-proof/task198-20260316t213409z-accum1-a1/`
- Remote replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task198-20260316t213409z-accum1-a1-window`
- Runtime truth:
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=1`
  - the replay reused the canonical RCA checkpoint `state-step-00001406`
- Live bounded replay status at the time of this ledger update:
  - the detached `1406 -> 1418` replay exited cleanly with `exit_code=0`
  - `current_optimizer_step=1418`
  - one scheduled eval completed there with
    `latest_eval_loss=8.293148636817932`
  - durable checkpoint
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task198-20260316t213409z-accum1-a1-window/diagnostic-run/checkpoints/state-step-00001418`
    exists
- Preferred `1500` continuation result:
  - the continuation launched directly from that clean `1418` checkpoint
  - the detached continuation exited with `exit_code=1`
  - `current_optimizer_step=1449`
  - `current_train_iteration=851`
  - no newer durable checkpoint beyond `1418` was minted
- Failure truth:
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - `first_non_finite_tensor=grad_norm`
  - `optimizer_step_attempted=false`
  - `optimizer_step_completed=false`
  - `microbatch_count=1` at the failing optimizer step
  - parameters and optimizer-state probes remained finite before the attempted
    optimizer step
- Operator conclusion:
  - accumulation `1` is stronger preferred-gate evidence than accumulation `2`
    because it reached `1449` instead of `1428`
  - accumulation `1` still did not satisfy the preferred `1500` gate
  - the next clean restart remains blocked
  - the documented fallback `1406 -> 1470` plus standalone eval gate is now
    the strongest next governed lane

## 2026-03-17: T198 Fallback Replay Also Failed At 1449, So Replay-Only RCA Is Exhausted

- Delivered tasks:
  - `docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md`
  - `docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md`
- Proof id:
  `task198-20260317t062816z-fallback1470-a1`
- Local proof artifact root:
  `build/verification/qwen-t198-proof/task198-20260317t062816z-fallback1470-a1/`
- Remote replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task198-20260317t062816z-fallback1470-a1-fallback1470`
- Runtime truth:
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=1`
  - the replay reused the canonical RCA checkpoint `state-step-00001406`
- Fallback replay result:
  - the detached fallback replay exited with `exit_code=1`
  - `current_optimizer_step=1449`
  - `current_train_iteration=851`
  - no truthful `1470` checkpoint was minted
- Failure truth:
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - `optimizer_step_attempted=false`
  - `optimizer_step_completed=false`
- Operator conclusion:
  - the preferred and fallback Story 29 proof gates are both negative on the
    current code path
  - replay-only RCA is now exhausted for this preserved Task 101 lane
  - the next active lane is `T206`:
    prove the true text-token span contract and land one code-bearing
    correction
  - after that correction lands, allow exactly one decisive Hemma proof:
    `1406 -> 1470` plus detached standalone eval
  - if that final post-fix proof still fails numerically before `1470`, stop
    bounded RCA on this lane and keep restart blocked until a new
    design/architecture story exists

## 2026-03-17: `T206` Offline Audit Proved `text_span_only` Is Still Prefix-Shaped

- Audit command:
  - `pdm run qwen-token-span-audit`
- Audit artifacts:
  - `build/verification/qwen-token-span-audit/task206-canonical-line101/report.json`
  - `build/verification/qwen-token-span-audit/task206-canonical-line101/report.md`
- Canonical sample source:
  - status artifact:
    `build/verification/qwen-t198-proof/task198-20260317t062816z-fallback1470-a1/fallback1470-status.json`
  - manifest line: `101`
  - train iteration: `851`
- Audit result:
  - current `text_span_only` still trains positions `0..136`
  - intended semantic text-only positions are `8..135`
  - current `text_span_only` therefore still leaks `9` non-semantic
    positions into the trainable span:
    `0..7` plus `136`
  - leaked ids are the prefix special/pad/BOS/EOS ids:
    `151644`, `77091`, `198`, `151671`, `151672`, `151673`
  - the current helper is still prefix-shaped, while the intended semantic
    span starts at `8`
- Operator conclusion:
  - the correction family cannot be another prefix-length tweak
  - `T206` now has concrete offline evidence that the canonical correction
    must move to an explicit position mask builder before the single final
    post-fix `1470 + standalone eval` proof is allowed

## 2026-03-17: `T206` Explicit Position-Mask Correction Removed The Offline Leakage

- Smallest post-fix regression:
  - `tests/sir_convert_a_lot/ml/qwen/training/test_training_rows.py::test_collate_fn_text_span_only_masks_only_semantic_text_positions`
- Post-fix audit command:
  - `pdm run qwen-token-span-audit --output-root build/verification/qwen-token-span-audit/task206-postfix-line101`
- Post-fix audit artifacts:
  - `build/verification/qwen-token-span-audit/task206-postfix-line101/report.json`
  - `build/verification/qwen-token-span-audit/task206-postfix-line101/report.md`
- Post-fix audit result:
  - current `text_span_only` now resolves to positions `8..135`
  - leaked positions are empty
  - leaked token ids are empty
  - leaked non-finite count is `0`
  - current trainable non-finite count equals intended semantic non-finite
    count: `128`
- Operator conclusion:
  - the explicit position-mask correction cleanly removes the previously
    audited prefix/pad/BOS/EOS leakage on the canonical failing sample
  - the next `T206` decision point is no longer whether leakage exists
  - the next `T206` decision point is whether this correction survives the
    remaining focused gates cleanly enough to become the single canonical fix
    before the final Hemma `1470 + standalone eval` proof

## 2026-03-17: `T206` Final Post-Fix Hemma Proof Failed At `1407`

- Proof package:
  - `task206-20260317t074600z-postfix1470-a1`
- Commands:
  - `pdm run qwen-t198-proof prepare --proof-id task206-20260317t074600z-postfix1470-a1 --gradient-accumulation-steps 1 --skip-build`
  - `pdm run qwen-t198-proof launch-fallback1470 --proof-id task206-20260317t074600z-postfix1470-a1`
- Artifacts:
  - `build/verification/qwen-t198-proof/task206-20260317t074600z-postfix1470-a1/proof-config.json`
  - `build/verification/qwen-t198-proof/task206-20260317t074600z-postfix1470-a1/fallback1470-launch.json`
  - `build/verification/qwen-t198-proof/task206-20260317t074600z-postfix1470-a1/fallback1470-status.json`
- Settings:
  - explicit position-mask correction committed
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=1`
- Result:
  - replay exited with `exit_code=1`
  - `current_optimizer_step=1407`
  - `current_train_iteration=809`
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - no truthful `1470` checkpoint was minted
- Operator conclusion:
  - the explicit position-mask correction removed the audited leakage, but it
    did not authorize restart on the preserved Task 101 lane
  - the single final post-fix proof still failed numerically before `1470`
  - detached standalone eval was correctly not launched
  - the Story 29 bounded-RCA stop rule is now triggered
  - `T199` remains blocked until a new design/architecture story defines the
    next lane

## 2026-03-17: `T210` Candidate 1 Rescue Proof Stayed Negative On The Inherited Lane

- Proof package:
  - `task210-20260317t104600z-candidate1-a1`
- Command:
  - `pdm run qwen-t198-proof launch-fallback1470 --proof-id task210-20260317t104600z-candidate1-a1`
- Result:
  - replay exited with `exit_code=1`
  - `current_optimizer_step=1407`
  - `current_train_iteration=809`
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - no truthful `1470` checkpoint was minted
- Operator conclusion:
  - Candidate 1 did not rescue the inherited `state-step-00001406` lane
  - that result alone still left open whether Candidate 1 might survive a
    fresh start

## 2026-03-17: `T211` Fresh-Start Candidate 1 Probe Failed At Step `1`

- Proof package:
  - `task211-20260317t130740z-freshstart-a4`
- Command:
  - `pdm run qwen-story30-freshstart-proof launch --proof-id task211-20260317t130740z-freshstart-a4`
- Artifacts:
  - `build/verification/qwen-story30-freshstart-proof/task211-20260317t130740z-freshstart-a4/proof-config.json`
  - `build/verification/qwen-story30-freshstart-proof/task211-20260317t130740z-freshstart-a4/launch.json`
  - `build/verification/qwen-story30-freshstart-proof/task211-20260317t130740z-freshstart-a4/status.json`
- Fresh-start posture:
  - base model `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
  - Candidate 1 semantic-only assembly path from `T207-T209`
  - mini-bundle train slice `swedish_pilot_train` lines `1..16`
  - launch placeholder eval row only; no held-out eval claim
- Result:
  - `status=exited`
  - `exit_code=1`
  - `current_optimizer_step=1`
  - `current_train_iteration=1`
  - `latest_checkpoint_found=false`
  - `eval_runs_completed=0`
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - `optimizer_step_attempted=false`
  - `optimizer_step_completed=false`
  - `pre_step_parameter_probes.first_non_finite_surface=null`
  - `pre_step_optimizer_state_probes.first_non_finite_surface=null`
  - `pre_clip_gradient_probes.probes.text_embedding.weight.nan_count=92160`
- First failing microbatch provenance:
  - manifest line `13`
  - manifest line `4`
- Operator conclusion:
  - Candidate 1 now has negative evidence on both the inherited-state rescue
    lane and the fresh-start short probe
  - replay-amassed inherited state is no longer the leading explanation for
    the current failure family
  - the next truthful discovery move is a single-step backward-lineage probe
    on the exact failing row pair, not another replay-family proof

## 2026-03-17: `T212` Backward-Lineage Probe Localized The Earliest Instrumented Non-Finite To `input_embeddings`

- Truthful proof package:
  - `task212-20260317t141500z-lineage-a3`
- Operational launch repairs preserved as evidence:
  - `task212-20260317t140500z-lineage-a1`
    - failed before probe execution because Docker could not bind-mount the
      canonical `/srv/scratch/.../mini-bundle` path directly
  - `task212-20260317t141000z-lineage-a2`
    - failed before probe execution because the container launch did not mount
      the repo, so the in-container probe module could not be imported
- Truthful artifacts:
  - `build/verification/qwen-story30-backward-lineage/task212-20260317t141500z-lineage-a3/proof-config.json`
  - `build/verification/qwen-story30-backward-lineage/task212-20260317t141500z-lineage-a3/status.json`
- Result:
  - detached worker `exit_code=0`
  - branch summaries:
    - `main_loss`: `both_rows`
    - `sub_talker_loss`: `both_rows`
    - `combined_loss`: `both_rows`
  - isolated rows:
    - line `13` failed independently
    - line `4` failed independently
  - pair branch RCA:
    - `gradient_rca.first_non_finite_surface=input_text_embedding.grad`
    - `parameter_gradient_probes.first_non_finite_surface=text_embedding.weight.grad`
  - earliest instrumented hook ordering:
    - `hidden_states` gradient stayed finite first
    - `talker_hidden_states` gradient stayed finite where present
    - `input_embeddings` was then the earliest hooked tensor with non-finite
      gradients
    - after that, non-finite gradients propagated to:
      `fused_auxiliary_embedding`,
      `input_codec_embedding`,
      `input_text_embedding`,
      `semantic_text_embeddings`
  - anomaly traces:
    - `main_loss` and `combined_loss` raised `MulBackward0`
    - `sub_talker_loss` raised `MmBackward0`
- Operator conclusion:
  - the row pair is not the decisive issue because both rows fail alone
  - replay-amassed inherited state is not the decisive issue because the
    truthful fresh-start probe reproduces the family directly
  - the current Candidate 1 assembly change is not where the earliest
    instrumented non-finite first appears
  - the next truthful discovery move is a talker-core backward trace between
    finite `hidden_states` gradients and non-finite `input_embeddings`
    gradients before any Candidate 3 implementation decision

## 2026-03-17: `T213` Localized The Earliest Non-Finite Hook To The Late-Middle Talker Core

- Truthful proof package:
  - `task213-20260317t143810z-talkercore-a1`
- Truthful artifacts:
  - `build/verification/qwen-story30-backward-lineage/task213-20260317t143810z-talkercore-a1/proof-config.json`
  - `build/verification/qwen-story30-backward-lineage/task213-20260317t143810z-talkercore-a1/status.json`
- Result:
  - detached worker `exit_code=0`
  - branch summaries:
    - `main_loss`: `both_rows`
    - `sub_talker_loss`: `both_rows`
    - `combined_loss`: `both_rows`
  - pair branch earliest talker-core hooks:
    - `main_loss`:
      `talker_core.layer_16.post_attention_layernorm`
    - `sub_talker_loss`:
      `talker_core.layer_15.output`
    - `combined_loss`:
      `talker_core.layer_16.post_attention_layernorm`
  - isolated rows:
    - line `13`:
      `main_loss` / `combined_loss` first localized at
      `talker_core.layer_16.output`
    - line `4`:
      `main_loss` / `combined_loss` first localized at
      `talker_core.layer_16.output`
    - both isolated `sub_talker_loss` runs first localized at
      `talker_core.layer_15.output`
  - anomaly traces:
    - pair `main_loss`: `MulBackward0`
    - pair `sub_talker_loss`: `MmBackward0`
    - pair `combined_loss`: `MulBackward0`
  - pair-main finite gradient magnitudes escalated sharply before the first
    non-finite hook:
    - `layer_27.output`: `1.07e-4`
    - `layer_26.output`: `2.34e3`
    - `layer_25.output`: `1.77e7`
    - `layer_24.output`: `1.04e11`
    - `layer_23.output`: `6.16e14`
    - `layer_22.output`: `1.73e18`
    - `layer_21.output`: `4.35e21`
    - `layer_20.output`: `1.22e25`
    - `layer_19.output`: `2.35e28`
    - `layer_18.output`: `6.75e31`
    - `layer_17.output`: `3.09e35`
    - `layer_16.output`: `3.19e38`
    - `layer_16.post_attention_layernorm`: first non-finite (`2048` NaNs)
  - pair-sub finite gradients stayed finite through:
    - `layer_17.output`: `8.68e33`
    - `layer_16.output`: `1.13e37`
    - `layer_15.output`: first non-finite (`3715` `Inf`s)
    - `layer_15.post_attention_layernorm`: then `4096` NaNs
- Operator conclusion:
  - the earliest non-finite hook is now localized inside the talker core, not
    just at `input_embeddings`
  - the late-middle talker stack around layer `16` / layer `15` is now the
    most truthful causal seam
  - Candidate `3` should not open yet because a smaller talker-core split is
    still yielding new causal signal
  - the next truthful move is a finer-grained layer `16` / layer `15`
    MLP-residual probe, not a replay and not a blind Candidate `3` jump

## Historical Reference Boundary

`docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md`
remains valuable as historical throughput and bottleneck evidence, but it is
not the live recovery plan for this lane. Use this ledger for current
training/eval recovery truth and use the March 13 reference for older
throughput analysis only.
