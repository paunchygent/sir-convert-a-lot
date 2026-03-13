---
id: story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma
title: Drive Task 101 Qwen training observability throughput and GPU saturation on Hemma
type: story
status: in_progress
priority: critical
created: '2026-03-13'
last_updated: '2026-03-13'
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

Out of scope for this story:

- changing the Qwen training objective,
- adding in-training evaluation,
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

## Acceptance Criteria

- [ ] The Task 101 runtime emits first-class tracker artifacts during live
  training, with MLflow as the primary run record and TensorBoard event files
  available for classical loss-curve inspection.
- [ ] The Task 101 live status surface updates during training and exposes
  truthful current-step, current-phase, latest-checkpoint, and tracker-run
  metadata instead of behaving like launch-only state.
- [ ] Long Task 101 runs automatically emit high-resolution resource evidence
  with `<= 1.0` second sampling, and the resulting summary can distinguish
  steady-state training windows from checkpoint-save windows.
- [ ] Long-run durable checkpoint cadence is no longer `2` steps by default,
  and Task 101 step accounting is explicit enough that operators can tell loop
  iterations from optimizer-update semantics.
- [ ] The dataloader and host-to-device transfer path expose evidence-backed
  tuned defaults for Hemma rather than relying on synchronous single-process
  defaults.
- [ ] Duplicate `ref_audio` rows no longer recompute `ref_mel` blindly in the
  hot path, and the team has an explicit documented decision on whether
  precomputed bundle-level mels are still required.
- [ ] Bounded PyTorch and ROCm profiling surfaces exist and produce reviewable
  traces for one Task 101 run without requiring ad hoc shell payloads.
- [ ] One real Hemma verification run demonstrates `>= 90%` median GPU busy
  during a steady-state non-checkpoint training window lasting at least
  `10` contiguous minutes.
- [ ] Story, epic, runbook, and reference docs all agree on the new
  saturation-oriented acceptance posture.

## Test Requirements

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task116_hemma_resource_monitor.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
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
