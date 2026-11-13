---
type: story
id: ST-SIRCON-05-03
title: Drive Qwen training observability throughput and GPU saturation on Hemma
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-05
links:
  decisions: []
acceptance_criteria:
- Qwen pilot runtime emits first-class tracker artifacts during live training, with
  MLflow primary and TensorBoard event files available for loss inspection.
- Task 101 live status exposes truthful current-step, phase, latest-checkpoint, and
  tracker-run metadata.
- Long Qwen pilot runs emit high-resolution resource evidence at no more than 1.0
  second sampling and distinguish steady-state from checkpoint-save windows.
- Durable checkpoint cadence is no longer 2 steps by default and step accounting distinguishes
  loop iterations from optimizer updates.
- Dataloader and host-to-device paths expose evidence-backed Hemma defaults rather
  than synchronous single-process defaults.
- Duplicate ref_audio rows do not recompute ref_mel blindly, with an explicit decision
  on bundle-level mels.
- Bounded PyTorch and ROCm profiling surfaces produce reviewable traces without ad
  hoc shell payloads.
- Canonical Task 101 performs real in-training held-out evaluation against swedish_checkpoint_dev
  and persists eval loss in tracker, status, and terminal reports.
- One Hemma verification run demonstrates at least 90 percent median GPU busy during
  a steady-state non-checkpoint window lasting at least 10 contiguous minutes.
- Story, epic, runbook, and reference docs agree on the saturation-oriented acceptance
  posture.
retired_ids:
- story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma
---
## Context

Source record: docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md

### Objective

> Turn the live Qwen Hemma lane from an operationally stable but
> under-observed and GPU-starved baseline into a truthfully monitored,
> throughput-optimized, saturation-oriented training pipeline.
>
> The formal performance gate for this story is:
>
> - `>= 90%` median GPU busy during steady-state non-checkpoint training windows
> - measured over at least `10` contiguous minutes
> - at `<= 1.0` second sampling
> - on real Hemma evidence written under `build/verification/`

## Epic Contract Slice

### Scope

> - Activate first-class experiment tracking with MLflow as the primary tracker
>   and TensorBoard as the secondary classical curve surface.
> - Make `status.json` and related Task 101 inspection output truthful during a
>   live run instead of mostly launch-time metadata.
> - Make high-resolution resource monitoring default for long Qwen pilot runs so
>   GPU, VRAM, CPU, and RAM evidence no longer depends on operator memory.
> - Remove the current throughput tax from over-aggressive durable-checkpoint
>   cadence and ambiguous step semantics.
> - Tune the dataloader and host-to-device transfer path so the GPU is fed
>   continuously rather than waiting on host-side preparation.
> - Eliminate repeated `ref_mel` recomputation at runtime and explicitly decide
>   whether the pilot-bundle contract must later persist precomputed mels.
> - Add bounded profiler surfaces for PyTorch and ROCm so bottleneck attribution
>   is evidence-backed rather than inferred from logs alone.
> - Define explicit Task 101 launch profiles and acceptance gates so future runs
>   distinguish smoke, profile, and long-saturation intents.
> - Triage the persistent MIOpen workspace warnings after the pipeline starvation
>   work lands, so backend-level issues are not confused with obvious host/I/O
>   bottlenecks.
> - Upgrade the held-out eval contract from metadata-only truth to a real
>   in-training eval loop so long Hemma runs expose held-out loss while they are
>   still in flight.
>
> Out of scope for this story:
>
> - changing the Qwen training objective,
> - changing the deterministic pilot-bundle ownership rule,
> - or undoing the detached Hemma launch architecture and bounded durable
>   checkpoint design.

## ADR Coverage

## Contract Inputs

## Live Verification Plan

### Implementation Blueprint (T161-T163)

> Execution order and ownership are fixed to keep SRP/LoC/complexity bounded:
>
> 1. `T161` runtime `ref_mel` cache and promotion decision.
> 1. `T162` bounded profiling surfaces.
> 1. `T163` launch profiles plus saturation gate.
> 1. Full local quality gates and docs gates.
> 1. Commit/push before any live pilot stop or relaunch.
> 1. Stop the active pilot only after the new code is pushed.
> 1. Pull on Hemma with `run-hemma` and relaunch through governed surfaces.
> 1. Verify the `>= 90%` saturation gate from monitor-backed evidence.
>
> Planned module ownership:
>
> - `T161`:
>   - add `scripts/devops/qwen_finetuning_patches/sft_12hz_ref_mel_cache.py`
>   - wire cache settings/metrics into `dataset.py`, `sft_12hz.py`,
>     `sft_12hz_tracking.py`, and Task 101 launcher/runtime/probe/status surfaces
>   - add bounded comparison surface
>     `scripts/sir_convert_a_lot/devops/run_task161_hemma_ref_mel_cache_comparison.py`
> - `T162`:
>   - add `scripts/devops/qwen_finetuning_patches/sft_12hz_profiling.py`
>   - add Qwen pilot runtime profiling orchestration module(s)
>   - add bounded profiling surface
>     `scripts/sir_convert_a_lot/devops/run_task162_hemma_task101_profiling.py`
> - `T163`:
>   - add `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_profiles.py`
>   - add `scripts/sir_convert_a_lot/devops/task101_qwen_saturation_gate.py`
>   - add gate runner
>     `scripts/sir_convert_a_lot/devops/run_task163_hemma_task101_saturation_gate.py`
>
> Verification posture for this blueprint:
>
> - no ad hoc `ssh hemma ...` for normal operations
> - no ad hoc `run-hemma --shell` profiler payloads
> - detached long-run Hemma execution only
> - monitor and saturation evidence written under `build/verification/`

### Current Implementation State (2026-03-14)

> - `T171` and the local implementation slice of `T173` are now in place.
> - The local implementation slice of `T172` is now in place:
>   aggressive throughput-profile metadata, budgeted length-bucketed batching,
>   and extracted codebook-fusion logic are landed in the training lane.
> - Task 101 bundles now persist canonical bundle-owned `ref_mel` artifacts and
>   prepared-manifest rows now carry explicit precomputed reference-input
>   provenance fields consumed by the in-container trainer.
> - The bundle orchestration surface was split under the SRP/LoC ceiling without
>   introducing compatibility aliases or shims.
> - A temporary legacy-bundle fallback remains in the launch/dataset path so
>   live `T172` validation can proceed against the existing Hemma bundle without
>   forcing an immediate two-day training reset; follow-on task `T174` removes
>   that fallback after one day of stable post-tuning throughput evidence.
> - Review-aligned follow-on task `T175` now tracks the remaining occupancy,
>   worker-truth attribution, strict rebuilt-bundle performance-lane enforcement,
>   phase-labeling, and auxiliary-codebook-collapse gaps that still block a fully
>   trustworthy saturation claim.
> - The current numerical-stability follow-on is now `T193`, which restores the
>   upstream no-projection fine-tuning contract, adds clip-boundary stage
>   forensics, and keeps the preserved Task 101 lane as the canonical RCA lane
>   while `T179` prepares the next bounded Hemma proof.
> - The first rebuilt-bundle aggressive throughput proof
>   (`task175-20260314t-throughput-a2`) failed with a non-finite loss at
>   optimizer step `4`.
> - Review of that rebuilt-bundle failure lane exposed concrete training-loop and
>   failure-reporting defects, so follow-on task `T180` now tracks the
>   accumulation-boundary audit, canonical failed-run report emission, and
>   accumulation-aware regression coverage required before trusting the next
>   bounded repro.
> - The next strict-recovery replay showed the remaining root cause is at the
>   optimizer boundary rather than in generic loss reporting alone, so follow-on
>   task `T186` now owns deterministic replay, targeted parameter/optimizer-state
>   probes, and the fail-closed guard that must land before another bounded
>   retry.
> - Follow-on task `T179` remains the dependent rebuilt-bundle Hemma repro that
>   runs only after `T180` and `T186` land and then decides whether the
>   numerical instability window is sufficiently bounded for another saturation
>   retry.
> - Story 28 with `T187-T191` is now delivered as the permanent
>   architecture-hardening lane. `RULE-095` and the extracted
>   `control_plane/`, `detached_runtime/`, `reporting/`, and bounded
>   `sft_12hz_*` runtime modules now block future god-file regression while the
>   numerical-stability work continues.
> - Story 29 with `T195-T199` now owns the bounded mitigation proof, fallback
>   gate, and restart decision required before the next clean Task 101 base
>   restart is allowed.
> - Follow-on task `T181` now tracks the real held-out eval loop required before
>   the team commits multi-hour Task 101 pilot time without in-run validation
>   loss truth.
> - Story 26 remains open because `T172` is still pending and `T173` still lacks
>   bounded Hemma evidence under `build/verification/`.

## Non-Goals

## Notes

### Tasks (Ordered)

> 1. `docs/backlog/tasks/task-156-activate-first-class-mlflow-and-accelerate-tracking-for-task-101-qwen-training.md`
> 1. `docs/backlog/tasks/task-157-add-truthful-live-heartbeat-and-phase-accounting-to-the-task-101-qwen-pilot-runtime.md`
> 1. `docs/backlog/tasks/task-158-make-high-resolution-hemma-resource-monitoring-default-for-long-task-101-qwen-runs.md`
> 1. `docs/backlog/tasks/task-159-correct-task-101-checkpoint-cadence-and-step-semantics-for-throughput-oriented-qwen-runs.md`
> 1. `docs/backlog/tasks/task-160-tune-the-task-101-qwen-dataloader-and-device-transfer-path-for-gpu-saturation.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-01-add-ref-mel-caching-and-a-promotion-decision-for-precomputed-qwen-reference-mels.md`
> 1. `docs/backlog/tasks/task-162-add-bounded-pytorch-and-rocm-profiling-surfaces-for-task-101-qwen-bottleneck-attribution.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-02-define-saturation-oriented-qwen-launch-profiles-and-acceptance-gates-on-hemma.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-03-persist-precomputed-qwen-reference-mels-in-the-pilot-bundle-and-training-manifest-contract.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-04-triage-and-remediate-miopen-workspace-warnings-in-the-task-101-rocm-qwen-training-lane.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-05-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-07-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-06-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-08-rebuild-the-task-101-bundle-on-the-t173-contract-and-remove-legacy-bundle-fallbacks-after-stable-throughput-proof.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-09-close-the-remaining-task-101-throughput-truth-gaps-from-the-review-alignment.md`
> 1. `docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md`
> 1. `docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-13-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-14-debug-the-task-101-pre-clip-text-embedding-gradient-failure-at-step-1405.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-11-add-real-in-training-held-out-eval-loop-to-qwen-training.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-12-add-standalone-eval-and-scheduled-train-stop-resume-control-for-qwen-training.md`
> 1. `docs/backlog/tasks/task-sircon-05-03-10-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md`

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review
