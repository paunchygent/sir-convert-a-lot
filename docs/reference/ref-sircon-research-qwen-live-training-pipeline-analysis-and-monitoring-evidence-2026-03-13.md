---
type: reference
id: REF-SIRCON-RESEARCH-qwen-live-training-pipeline-analysis-and-monitoring-evidence-2026-03-13
title: Qwen Live Training Pipeline Analysis and Monitoring Evidence (2026-03-13)
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: research
summary: Qwen Live Training Pipeline Analysis and Monitoring Evidence (2026-03-13)
retired_ids:
- REF-qwen-live-training-pipeline-analysis-2026-03-13
---

## Research Purpose And Boundary

## Evidence And Sources

## Findings And Interpretation

## Evidence Gaps And Follow-Up

## Historical Source Content

### Purpose

Persist one detailed, evidence-backed analysis of the live Qwen Swedish
Qwen3-TTS Hemma training pipeline as observed on Friday, 2026-03-13, including:

- exact live run state and command surfaces,
- training-loss behavior with smoothed interpretation,
- GPU and host resource evidence,
- confirmed robust surfaces that should be treated as off-limits in the next
  optimization slice,
- confirmed issues and high-confidence bottleneck hypotheses,
- and concrete observability / throughput follow-up priorities.

This report is intentionally detailed enough to serve as the canonical
reference for the next monitoring, throughput, and training-program hardening
tasks without forcing the next operator to reconstruct the evidence by hand.

### Historical Scope Note (2026-03-15)

This document remains the detailed historical analysis for the March 13 live
throughput/bottleneck window. It is no longer the canonical operator plan for
the preserved Task 101 recovery lane.

For the live training/eval recovery posture after Task 182/183/185:

- use
  `docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md`
  as the operator-facing progress ledger
- treat this March 13 report as historical throughput evidence only
- do not use its checkpoint cadence, live-state assumptions, or run posture as
  the current recovery plan

### Addendum: T161 and T162 Evidence Update (2026-03-13 Evening)

What the evidence shows (not guesses):

- `T161` cache-off run (`task161-20260313t212725z-cache-off`):
  steady-state train GPU median = `26%`
- `T161` cache-on run (`task161-20260313t212725z-cache-on`):
  steady-state train GPU median = `8%`
- `T162` profiling run (`task162-20260313t220644z-profile`):
  steady-state train GPU median = `3%`
- in both `T161` runs and `T162`, runtime cache metrics are effectively dead:
  `cache_hits=0`, `cache_misses=0`, `cache_size=0`
- `T162` ROCm profiling attribution:
  - HIP API total: `98.74s`
  - kernel total: `102.08s`
  - memory-copy trace total: `1.73s`
  - top HIP API time:
    - `hipLaunchKernel`: `44.18s`
    - `hipMemcpyWithStream`: `21.52s`
    - `hipEventSynchronize`: `17.89s`

Root-cause conclusion:

- the lane remains host-orchestration/synchronization bound
  (kernel launch + sync overhead), not compute-saturated
- runtime `ref_mel` cache is not engaged in practice for this lane and cannot
  currently lift saturation
- training is also running with persistent `NaN` loss, which undermines
  throughput and saturation evidence quality

### Decisioned Optimization Targets

The optimization program derived from this report uses a deliberately hard
throughput target.

Primary acceptance target:

- `>= 90%` median GPU busy during steady-state non-checkpoint training windows
- window length:
  - at least `10` contiguous minutes
- sampling interval:
  - `<= 1.0` second
- excluded phases:
  - startup / model load
  - intentional durable-checkpoint save windows
  - terminal teardown / stop handling

Secondary target:

- keep the overall long-run GPU-busy median as high as practical once
  checkpoint and orchestration windows are included, but do not use the
  full-run median as the canonical gate because it mixes compute and intended
  pause phases.

Failure threshold for the optimization story:

- anything below `90%` median GPU busy in the defined steady-state training
  window remains insufficient and should not be treated as success

Working interpretation:

- `100%` wall-clock GPU busy is still not the formal gate because a truthful
  training pipeline includes intentional host and checkpoint phases
- however, a target in the `50-70%` range is explicitly rejected for this lane
  as too weak relative to the hardware and the current optimization objective

### Scope

This document analyzes the active detached Task 101 Hemma training launch:

- launch id: `task101-20260313t102144z`
- container name: `task101-20260313t102144z-container`
- live run root:
  - `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z`
- live launch root:
  - `/srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot/task101-20260313t102144z`

It also includes the ad hoc-but-committed Task 116 Hemma resource monitor that
was launched during this analysis window:

- monitor launch id: `task116-resource-20260313t135754z`
- monitor launch root:
  - `/srv/scratch/sir-convert-a-lot/build/verification/task-116-hemma-resource-monitor/task116-resource-20260313t135754z`

### Evidence Window

The most important snapshots used in this analysis were collected at these UTC
timestamps:

- `2026-03-13T13:45:38Z`
  - Task 101 status snapshot with live loss tail through step `620`
- `2026-03-13T13:57:54Z`
  - Task 116 resource monitor launch
- `2026-03-13T13:58:22Z`
  - Task 116 early status check confirming GPU/host sampling works
- `2026-03-13T14:06:39Z`
  - latest durable checkpoint step `666`
- `2026-03-13T14:07:47Z`
  - Task 101 status snapshot with loss tail through step `660`
- `2026-03-13T14:08:02Z`
  - Task 116 summary window end (`41` samples)

All timestamps below are reported in UTC unless explicitly noted otherwise.

### Executive Summary

The current Task 101 pipeline is operationally stable but materially
under-observed and almost certainly underutilizing the GPU.

What is working:

- the detached Hemma launch surface works,
- the training container stays alive,
- the training loop advances,
- the run is not OOM-killed,
- durable checkpoints are being written and rotated,
- the live run continues to make training-loss progress,
- and a detached resource monitor can be run in parallel without disturbing the
  training container.

What is not working well:

- the live monitoring story is weak,
- the TensorBoard tracker path is half-wired but not actually producing events,
- `status.json` is not a live heartbeat surface,
- logs are dominated by raw per-step loss plus MIOpen warnings,
- and the observed GPU busy percentage is far too low for a serious throughput
  run.

Most important confirmed live evidence:

- Task 116 measured `gpu_busy_percent_median = 5` and
  `gpu_busy_percent_max = 12` over `41` samples, while
  `gpu_memory_used_percent_median = 68`
- Task 101 is currently saving durable checkpoints every `2` steps
- each retained durable checkpoint is about `11G`
- the dataset path still does on-demand `librosa.load(...)` and `ref_mel`
  extraction inside `__getitem__`
- the `DataLoader` currently uses no explicit `num_workers`,
  `pin_memory`, `persistent_workers`, or `prefetch_factor`
- the run root contains no TensorBoard event files or other live scalar
  tracking artifacts

High-confidence interpretation:

- the GPU is resident but starved,
- the most likely dominant causes are dataloader / CPU-side preparation plus
  aggressive durable-checkpoint I/O,
- and the next optimization story should be judged against the
  `>= 90%` steady-state median GPU-busy target defined above before optimizer
  retuning is treated as the main lever.

### Current Pipeline Shape

The live Task 101 training path is now structurally split into these major
surfaces:

- launcher / CLI:
  - `scripts/sir_convert_a_lot/cli/ml/qwen_train.py`
- detached runtime helpers:
  - `scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/launch_service.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/models.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/reporting`
- in-container probe:
  - `scripts/sir_convert_a_lot/cli/ml/qwen_smoke.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/reporting`
- patched upstream trainer:
  - `scripts/devops/qwen_finetuning_patches/sft_12hz.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_checkpointing.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_training_rows.py`
  - `scripts/devops/qwen_finetuning_patches/dataset.py`

The active training launch consumes the deterministic frozen pilot bundle:

- pilot bundle root:
  - `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h`
- train manifest:
  - `swedish_pilot_train.prepared.jsonl`
- held-out eval manifest:
  - `swedish_checkpoint_dev.prepared.jsonl`

Important contract note:

- the detached Task 101 lane explicitly records the eval manifest path in
  launch and status metadata,
- but the upstream patched `sft_12hz.py` remains a train-only loop and does
  not perform in-training evaluation.

That limitation is currently deliberate and contractually truthful. It should
not be silently changed inside a monitoring or throughput task.

### Evidence Summary

- Task 101 launch `task101-20260313t102144z` and the parallel Task 116 monitor
  remained operational: the container advanced, avoided OOM termination, and
  wrote durable checkpoints. The 41-sample monitor window measured median GPU
  busy `5%` (maximum `12%`) and median GPU memory `68%`.
- The T161 cache comparison measured `26%` median GPU busy with cache off and
  `8%` with cache on; T162 profiling measured `3%`. All runs reported
  `cache_hits=0`, `cache_misses=0`, and `cache_size=0`. T162 attributed
  `98.74s` to HIP API calls, `102.08s` to kernels, and `1.73s` to copies,
  with launch/synchronization calls dominant.
- Durable checkpoints were approximately `11G` and saved every two steps in
  the observed run. The dataset still performed on-demand `librosa.load` and
  reference-mel extraction in `__getitem__`; the DataLoader had no explicit
  worker, pinning, persistence, or prefetch configuration. No TensorBoard event
  files or live scalar artifacts were present.
- The evidence supports a host-orchestration/synchronization bottleneck rather
  than compute saturation. Runtime reference-mel caching was not active, and
  persistent `NaN` loss made throughput/saturation evidence less trustworthy.

### Code-Grounded Findings

- The detached launch architecture, deterministic pilot-bundle ownership,
  durable checkpoint staging, containerized ROCm runtime, multi-speaker model
  patch direction, and train-only loop with explicit eval-manifest recording
  are confirmed robust surfaces. Subsequent optimization must preserve them.
- Monitoring is incomplete: trainer tracking is half-wired, logged loss is raw
  and composite, `status.json` is not a live heartbeat, Task 116 is not default
  wired into Task 101, and the report/training summary are terminal artifacts.
- Confirmed issues are severe GPU underutilization, checkpoint I/O overhead,
  insufficient live monitoring, noisy logs, weak dataloader throughput, unclear
  step semantics, and helper monitoring hidden outside the default launch path.
- High-confidence inferences are that data/I/O orchestration contributes more
  than pure GPU compute, checkpoint writes materially reduce throughput, and
  optimizer retuning should wait until the data path, checkpoint cadence,
  heartbeat, and loss integrity are repaired.

### Deliberate Limits

- This report is historical March 13 throughput evidence, not the current
  Task 101 recovery plan; use the March 15 progress ledger for that posture.
- It does not prove optimizer quality, in-training evaluation, or a final
  promotion decision. Task 116 was not default-wired, and the training summary
  is terminal rather than a live state surface.
- The formal acceptance gate remains at least `90%` median GPU busy for a
  contiguous 10-minute steady-state non-checkpoint window sampled at no more
  than one second. Full-run medians and the former `50–70%` target are not
  sufficient.

### Recommended Next-Slice Boundaries

1. Repair data loading and precompute or otherwise bound reference-mel work;
   capture row-level timing and dataloader wait evidence.
2. Reduce checkpoint cadence and measure checkpoint duration separately from
   compute windows; retain bounded checkpoint recovery proof.
3. Add a truthful heartbeat, structured loss/range diagnostics, and default
   resource-monitor integration without changing train-only semantics.
4. Re-run the defined 10-minute gate before tuning optimizer hyperparameters.
   Keep eval-loop work, model bake-offs, and production promotion in separately
   governed tasks.

### Evidence References

The retained evidence includes the Task 101 status/checkpoint snapshots, Task
116 resource-monitor bundle, T161/T162 cache and ROCm profiles, and the live
launch/reporting code paths listed in `Current Pipeline Shape`. These artifacts
are historical observations and should be read with their timestamps and
limitations; they do not authorize production changes.

### Bottom Line

The lane is operationally durable but GPU-starved and under-observed. The next
slice should target host-side data and checkpoint orchestration, restore
truthful live monitoring, and prove the `>=90%` steady-state gate before any
optimizer or promotion decision.
