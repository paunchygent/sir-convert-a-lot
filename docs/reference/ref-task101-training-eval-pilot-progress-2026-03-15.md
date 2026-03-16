---
type: reference
id: REF-task101-training-eval-pilot-progress-2026-03-15
title: Task 101 Training/Eval Pilot Progress Ledger (2026-03-15)
status: active
created: 2026-03-15
updated: 2026-03-16
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
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
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

## Historical Reference Boundary

`docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md`
remains valuable as historical throughput and bottleneck evidence, but it is
not the live recovery plan for this lane. Use this ledger for current
training/eval recovery truth and use the March 13 reference for older
throughput analysis only.
