---
id: story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma
title: Drive Task 101 Qwen training observability throughput and GPU saturation on Hemma
type: story
status: in_progress
priority: critical
created: '2026-03-13'
last_updated: '2026-03-15'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-116-expand-rixvox-staging-and-run-a-sustained-detached-row-processing-window-for-the-bounded-hemma-pilot.md
  - docs/backlog/tasks/task-118-profile-the-qwen-finetuning-dataloader-and-decide-whether-to-precompute-ref-mels.md
  - docs/backlog/tasks/task-153-retain-only-bounded-durable-qwen-training-checkpoints-and-guard-scratch-capacity-on-hemma.md
  - docs/backlog/tasks/task-154-remediate-t153-checkpoint-compatibility-scratch-guard-sizing-and-docs-proof-drift.md
  - docs/backlog/tasks/task-155-refactor-qwen-checkpoint-and-task-101-pilot-god-files-into-srp-modules.md
  - docs/backlog/tasks/task-156-activate-first-class-mlflow-and-accelerate-tracking-for-task-101-qwen-training.md
  - docs/backlog/tasks/task-157-add-truthful-live-heartbeat-and-phase-accounting-to-the-task-101-qwen-pilot-runtime.md
  - docs/backlog/tasks/task-158-make-high-resolution-hemma-resource-monitoring-default-for-long-task-101-qwen-runs.md
  - docs/backlog/tasks/task-159-correct-task-101-checkpoint-cadence-and-step-semantics-for-throughput-oriented-qwen-runs.md
  - docs/backlog/tasks/task-160-tune-the-task-101-qwen-dataloader-and-device-transfer-path-for-gpu-saturation.md
  - docs/backlog/tasks/task-161-add-ref-mel-caching-and-a-promotion-decision-for-precomputed-task-101-qwen-reference-mels.md
  - docs/backlog/tasks/task-162-add-bounded-pytorch-and-rocm-profiling-surfaces-for-task-101-qwen-bottleneck-attribution.md
  - docs/backlog/tasks/task-163-define-saturation-oriented-task-101-qwen-launch-profiles-and-acceptance-gates-on-hemma.md
  - docs/backlog/tasks/task-164-persist-precomputed-task-101-qwen-reference-mels-in-the-pilot-bundle-and-training-manifest-contract.md
  - docs/backlog/tasks/task-165-triage-and-remediate-miopen-workspace-warnings-in-the-task-101-rocm-qwen-training-lane.md
  - docs/backlog/tasks/task-171-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards.md
  - docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md
  - docs/backlog/tasks/task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md
  - docs/backlog/tasks/task-174-rebuild-the-task-101-bundle-on-the-t173-contract-and-remove-legacy-bundle-fallbacks-after-stable-throughput-proof.md
  - docs/backlog/tasks/task-175-close-the-remaining-task-101-throughput-truth-gaps-from-the-review-alignment.md
  - docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/tasks/task-194-debug-the-task-101-pre-clip-text-embedding-gradient-failure-at-step-1405.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-187-define-and-codify-qwen-training-control-plane-architecture-rules.md
  - docs/backlog/tasks/task-188-refactor-host-qwen-cli-control-plane-use-cases-out-of-qwen-train-py.md
  - docs/backlog/tasks/task-189-replace-qwen-detached-orchestrator-with-bounded-runtime-modules.md
  - docs/backlog/tasks/task-190-replace-qwen-reporting-module-with-bounded-reporting-packages.md
  - docs/backlog/tasks/task-191-split-qwen-patched-training-loop-into-bounded-runtime-modules.md
  - docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md
  - docs/backlog/tasks/task-181-add-real-in-training-held-out-eval-loop-to-task-101-qwen-training.md
  - docs/backlog/tasks/task-182-add-standalone-eval-and-scheduled-train-stop-resume-control-for-task-101-qwen-training.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - https://huggingface.co/docs/accelerate/en/usage_guides/tracking
  - https://www.mlflow.org/docs/latest/ml/tracking/
  - https://www.mlflow.org/docs/latest/ml/tracking/system-metrics/
  - https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html
  - https://docs.pytorch.org/tutorials/recipes/recipes/profiler_recipe.html
  - https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/docs-6.3.0/how-to/using-rocprofv3.html
labels:
  - qwen
  - finetuning
  - monitoring
  - throughput
  - rocm
  - hemma
  - mlflow
---

Implementation slice with acceptance-driven scope.

## Objective

Turn the live Task 101 Qwen Hemma lane from an operationally stable but
under-observed and GPU-starved baseline into a truthfully monitored,
throughput-optimized, saturation-oriented training pipeline.

The formal performance gate for this story is:

- `>= 90%` median GPU busy during steady-state non-checkpoint training windows
- measured over at least `10` contiguous minutes
- at `<= 1.0` second sampling
- on real Hemma evidence written under `build/verification/`

## Scope

- Activate first-class experiment tracking with MLflow as the primary tracker
  and TensorBoard as the secondary classical curve surface.
- Make `status.json` and related Task 101 inspection output truthful during a
  live run instead of mostly launch-time metadata.
- Make high-resolution resource monitoring default for long Task 101 runs so
  GPU, VRAM, CPU, and RAM evidence no longer depends on operator memory.
- Remove the current throughput tax from over-aggressive durable-checkpoint
  cadence and ambiguous step semantics.
- Tune the dataloader and host-to-device transfer path so the GPU is fed
  continuously rather than waiting on host-side preparation.
- Eliminate repeated `ref_mel` recomputation at runtime and explicitly decide
  whether the pilot-bundle contract must later persist precomputed mels.
- Add bounded profiler surfaces for PyTorch and ROCm so bottleneck attribution
  is evidence-backed rather than inferred from logs alone.
- Define explicit Task 101 launch profiles and acceptance gates so future runs
  distinguish smoke, profile, and long-saturation intents.
- Triage the persistent MIOpen workspace warnings after the pipeline starvation
  work lands, so backend-level issues are not confused with obvious host/I/O
  bottlenecks.
- Upgrade the held-out eval contract from metadata-only truth to a real
  in-training eval loop so long Hemma runs expose held-out loss while they are
  still in flight.

Out of scope for this story:

- changing the Qwen training objective,
- changing the deterministic pilot-bundle ownership rule,
- or undoing the detached Hemma launch architecture and bounded durable
  checkpoint design.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-156-activate-first-class-mlflow-and-accelerate-tracking-for-task-101-qwen-training.md`
1. `docs/backlog/tasks/task-157-add-truthful-live-heartbeat-and-phase-accounting-to-the-task-101-qwen-pilot-runtime.md`
1. `docs/backlog/tasks/task-158-make-high-resolution-hemma-resource-monitoring-default-for-long-task-101-qwen-runs.md`
1. `docs/backlog/tasks/task-159-correct-task-101-checkpoint-cadence-and-step-semantics-for-throughput-oriented-qwen-runs.md`
1. `docs/backlog/tasks/task-160-tune-the-task-101-qwen-dataloader-and-device-transfer-path-for-gpu-saturation.md`
1. `docs/backlog/tasks/task-161-add-ref-mel-caching-and-a-promotion-decision-for-precomputed-task-101-qwen-reference-mels.md`
1. `docs/backlog/tasks/task-162-add-bounded-pytorch-and-rocm-profiling-surfaces-for-task-101-qwen-bottleneck-attribution.md`
1. `docs/backlog/tasks/task-163-define-saturation-oriented-task-101-qwen-launch-profiles-and-acceptance-gates-on-hemma.md`
1. `docs/backlog/tasks/task-164-persist-precomputed-task-101-qwen-reference-mels-in-the-pilot-bundle-and-training-manifest-contract.md`
1. `docs/backlog/tasks/task-165-triage-and-remediate-miopen-workspace-warnings-in-the-task-101-rocm-qwen-training-lane.md`
1. `docs/backlog/tasks/task-171-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards.md`
1. `docs/backlog/tasks/task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md`
1. `docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md`
1. `docs/backlog/tasks/task-174-rebuild-the-task-101-bundle-on-the-t173-contract-and-remove-legacy-bundle-fallbacks-after-stable-throughput-proof.md`
1. `docs/backlog/tasks/task-175-close-the-remaining-task-101-throughput-truth-gaps-from-the-review-alignment.md`
1. `docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md`
1. `docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md`
1. `docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md`
1. `docs/backlog/tasks/task-194-debug-the-task-101-pre-clip-text-embedding-gradient-failure-at-step-1405.md`
1. `docs/backlog/tasks/task-181-add-real-in-training-held-out-eval-loop-to-task-101-qwen-training.md`
1. `docs/backlog/tasks/task-182-add-standalone-eval-and-scheduled-train-stop-resume-control-for-task-101-qwen-training.md`
1. `docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md`

## Implementation Blueprint (T161-T163)

Execution order and ownership are fixed to keep SRP/LoC/complexity bounded:

1. `T161` runtime `ref_mel` cache and promotion decision.
1. `T162` bounded profiling surfaces.
1. `T163` launch profiles plus saturation gate.
1. Full local quality gates and docs gates.
1. Commit/push before any live pilot stop or relaunch.
1. Stop the active pilot only after the new code is pushed.
1. Pull on Hemma with `run-hemma` and relaunch through governed surfaces.
1. Verify the `>= 90%` saturation gate from monitor-backed evidence.

Planned module ownership:

- `T161`:
  - add `scripts/devops/qwen_finetuning_patches/sft_12hz_ref_mel_cache.py`
  - wire cache settings/metrics into `dataset.py`, `sft_12hz.py`,
    `sft_12hz_tracking.py`, and Task 101 launcher/runtime/probe/status surfaces
  - add bounded comparison surface
    `scripts/sir_convert_a_lot/devops/run_task161_hemma_ref_mel_cache_comparison.py`
- `T162`:
  - add `scripts/devops/qwen_finetuning_patches/sft_12hz_profiling.py`
  - add Task 101 runtime profiling orchestration module(s)
  - add bounded profiling surface
    `scripts/sir_convert_a_lot/devops/run_task162_hemma_task101_profiling.py`
- `T163`:
  - add `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_profiles.py`
  - add `scripts/sir_convert_a_lot/devops/task101_qwen_saturation_gate.py`
  - add gate runner
    `scripts/sir_convert_a_lot/devops/run_task163_hemma_task101_saturation_gate.py`

Verification posture for this blueprint:

- no ad hoc `ssh hemma ...` for normal operations
- no ad hoc `run-hemma --shell` profiler payloads
- detached long-run Hemma execution only
- monitor and saturation evidence written under `build/verification/`

## Latest Hemma Evidence Snapshot (2026-03-13)

What the evidence shows from the bounded `T161` and `T162` runs:

- `T161` cache-off run (`task161-20260313t212725z-cache-off`):
  steady-state train GPU median = `26%`
- `T161` cache-on run (`task161-20260313t212725z-cache-on`):
  steady-state train GPU median = `8%`
- `T162` profiling run (`task162-20260313t220644z-profile`):
  steady-state train GPU median = `3%`
- in both `T161` runs and `T162`, `ref_mel_cache` stats are effectively dead:
  `cache_hits=0`, `cache_misses=0`, `cache_size=0`
- `T162` ROCm profiling attribution:
  - HIP API total: `98.74s`
  - kernel total: `102.08s`
  - memory-copy trace total: `1.73s`
  - top HIP API time:
    - `hipLaunchKernel` = `44.18s`
    - `hipMemcpyWithStream` = `21.52s`
    - `hipEventSynchronize` = `17.89s`

Root-cause conclusion from this evidence:

- the lane is still host-orchestration/synchronization bound
  (kernel launch + sync overhead), not compute-saturated
- runtime `ref_mel` cache is not engaged in practice for this lane and cannot
  currently lift saturation
- the lane has a separate quality blocker: persistent `NaN` training loss,
  which undermines throughput/saturation trustworthiness

## Current Implementation State (2026-03-14)

- `T171` and the local implementation slice of `T173` are now in place.
- The local implementation slice of `T172` is now in place:
  aggressive throughput-profile metadata, budgeted length-bucketed batching,
  and extracted codebook-fusion logic are landed in the training lane.
- Task 101 bundles now persist canonical bundle-owned `ref_mel` artifacts and
  prepared-manifest rows now carry explicit precomputed reference-input
  provenance fields consumed by the in-container trainer.
- The bundle orchestration surface was split under the SRP/LoC ceiling without
  introducing compatibility aliases or shims.
- A temporary legacy-bundle fallback remains in the launch/dataset path so
  live `T172` validation can proceed against the existing Hemma bundle without
  forcing an immediate two-day training reset; follow-on task `T174` removes
  that fallback after one day of stable post-tuning throughput evidence.
- Review-aligned follow-on task `T175` now tracks the remaining occupancy,
  worker-truth attribution, strict rebuilt-bundle performance-lane enforcement,
  phase-labeling, and auxiliary-codebook-collapse gaps that still block a fully
  trustworthy saturation claim.
- The current numerical-stability follow-on is now `T193`, which restores the
  upstream no-projection fine-tuning contract, adds clip-boundary stage
  forensics, and keeps the preserved Task 101 lane as the canonical RCA lane
  while `T179` prepares the next bounded Hemma proof.
- The first rebuilt-bundle aggressive throughput proof
  (`task175-20260314t-throughput-a2`) failed with a non-finite loss at
  optimizer step `4`.
- Review of that rebuilt-bundle failure lane exposed concrete training-loop and
  failure-reporting defects, so follow-on task `T180` now tracks the
  accumulation-boundary audit, canonical failed-run report emission, and
  accumulation-aware regression coverage required before trusting the next
  bounded repro.
- The next strict-recovery replay showed the remaining root cause is at the
  optimizer boundary rather than in generic loss reporting alone, so follow-on
  task `T186` now owns deterministic replay, targeted parameter/optimizer-state
  probes, and the fail-closed guard that must land before another bounded
  retry.
- Follow-on task `T179` remains the dependent rebuilt-bundle Hemma repro that
  runs only after `T180` and `T186` land and then decides whether the
  numerical instability window is sufficiently bounded for another saturation
  retry.
- Story 28 with `T187-T191` is now delivered as the permanent
  architecture-hardening lane. `RULE-095` and the extracted
  `control_plane/`, `detached_runtime/`, `reporting/`, and bounded
  `sft_12hz_*` runtime modules now block future god-file regression while the
  numerical-stability work continues.
- Follow-on task `T181` now tracks the real held-out eval loop required before
  the team commits multi-hour Task 101 pilot time without in-run validation
  loss truth.
- Story 26 remains open because `T172` is still pending and `T173` still lacks
  bounded Hemma evidence under `build/verification/`.

## Acceptance Criteria

- [x] The Task 101 runtime emits first-class tracker artifacts during live
  training, with MLflow as the primary run record and TensorBoard event files
  available for classical loss-curve inspection.
- [x] The Task 101 live status surface updates during training and exposes
  truthful current-step, current-phase, latest-checkpoint, and tracker-run
  metadata instead of behaving like launch-only state.
- [x] Long Task 101 runs automatically emit high-resolution resource evidence
  with `<= 1.0` second sampling, and the resulting summary can distinguish
  steady-state training windows from checkpoint-save windows.
- [x] Long-run durable checkpoint cadence is no longer `2` steps by default,
  and Task 101 step accounting is explicit enough that operators can tell loop
  iterations from optimizer-update semantics.
- [x] The dataloader and host-to-device transfer path expose evidence-backed
  tuned defaults for Hemma rather than relying on synchronous single-process
  defaults.
- [x] Duplicate `ref_audio` rows no longer recompute `ref_mel` blindly in the
  hot path, and the team has an explicit documented decision on whether
  precomputed bundle-level mels are still required.
- [x] Bounded PyTorch and ROCm profiling surfaces exist and produce reviewable
  traces for one Task 101 run without requiring ad hoc shell payloads.
- [ ] The canonical Task 101 lane performs real in-training held-out eval
  against `swedish_checkpoint_dev` and persists eval loss in tracker, status,
  and terminal report artifacts.
- [ ] One real Hemma verification run demonstrates `>= 90%` median GPU busy
  during a steady-state non-checkpoint training window lasting at least
  `10` contiguous minutes.
- [x] Story, epic, runbook, and reference docs all agree on the new
  saturation-oriented acceptance posture.

## Test Requirements

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_qwen_training_tracking.py tests/sir_convert_a_lot/test_task101_qwen_status_reporter.py tests/sir_convert_a_lot/test_qwen_training_ref_mel_cache.py tests/sir_convert_a_lot/test_task161_qwen_ref_mel_cache_comparison.py tests/sir_convert_a_lot/test_qwen_training_profiling.py tests/sir_convert_a_lot/test_task101_qwen_profiling.py tests/sir_convert_a_lot/test_task101_qwen_resource_monitor.py tests/sir_convert_a_lot/test_qwen_training_dataloader_tuning.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Real Hemma evidence for tracker artifacts, status heartbeat, monitor
  summary, and a `>= 90%` steady-state GPU-busy window is written under
  `build/verification/`.

## Done Definition

The repo has one explicit throughput- and observability-oriented Task 101
hardening story that:

- preserves the robust detached Task 101 / bounded-checkpoint architecture,
- adds first-class tracking and truthful live monitoring,
- removes the most obvious input-pipeline and checkpoint-I/O starvation
  bottlenecks,
- and defines success in terms of measured steady-state GPU saturation on
  Hemma rather than intuition.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
