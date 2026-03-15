---
type: reference
id: REF-task101-training-eval-pilot-progress-2026-03-15
title: Task 101 Training/Eval Pilot Progress Ledger (2026-03-15)
status: active
created: 2026-03-15
updated: 2026-03-15
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
- treat `state-step-00001238` as the canonical next strict resume target
- do not resume from `1236` again unless a deliberate compatibility experiment
  requires it
- record future live training/eval progress here, not in the skill doc
- treat `T186` as the delivered optimizer-boundary remediation and proof slice
  that now informs the next `T179` bounded-retry decision
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
- the original legacy launch snapshot still carries stale checkpoint cadence
  settings (`2/100/2`), so the next strict resume must pass explicit control
  overrides rather than inheriting those stale values

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

Removed after the canonical relaunch was confirmed healthy:

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

## Superseded Operator Plan

The abandoned plan is:

- “run standalone eval on `1236`, then resume from `1236` again”

That plan is now superseded because:

- the probe already minted `1238`
- `1238` preserves more training progress
- `1238` has a truthful compatible cursor for the replacement bundle
- rolling back to `1236` would spend operator time for no gain
- after the strict `1238` relaunch failed at `1358`, the later
  instrumented replay failed at `1408`, and the guarded diagnostic then failed
  closed at `1405`, the next move is no longer "resume immediately again"; it
  is "use the completed `T186` proof to decide the next bounded `T179` retry"

## Canonical Next Step

Do not relaunch the recovered training lane blindly.

The next canonical action is to use the completed `T186` proof so operators
can decide whether and how to run the next bounded `T179` retry:

- the guarded proof already established that `optimizer.step()` is skipped
  before the corrupt update is applied at step `1405`
- the remaining decision is whether the rebuilt-bundle lane is now sufficiently
  bounded to justify the next `T179` stability retry, and under what exact
  runtime controls

## Historical Reference Boundary

`docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md`
remains valuable as historical throughput and bottleneck evidence, but it is
not the live recovery plan for this lane. Use this ledger for current
training/eval recovery truth and use the March 13 reference for older
throughput analysis only.
