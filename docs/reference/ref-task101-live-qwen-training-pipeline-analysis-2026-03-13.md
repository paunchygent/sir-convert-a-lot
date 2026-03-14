---
type: reference
id: REF-task101-live-qwen-training-pipeline-analysis-2026-03-13
title: Task 101 Live Qwen Training Pipeline Analysis and Monitoring Evidence (2026-03-13)
status: active
created: 2026-03-13
updated: 2026-03-13
owners:
  - platform
tags:
  - qwen
  - tts
  - training
  - monitoring
  - hemma
  - rocm
  - task101
links:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
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
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - https://huggingface.co/docs/accelerate/en/usage_guides/tracking
  - https://mlflow.org/docs/latest/ml/tracking/
  - https://mlflow.org/docs/latest/ml/tracking/system-metrics/
  - https://docs.pytorch.org/tutorials/recipes/recipes/profiler_recipe.html
---

## Purpose

Persist one detailed, evidence-backed analysis of the live Task 101 Swedish
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

## Addendum: T161 and T162 Evidence Update (2026-03-13 Evening)

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

## Decisioned Optimization Targets

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

## Scope

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

## Evidence Window

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

## Executive Summary

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

## Current Pipeline Shape

The live Task 101 training path is now structurally split into these major
surfaces:

- launcher / CLI:
  - `scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py`
- detached runtime helpers:
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime_contract.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime_artifacts.py`
- in-container probe:
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe_reporting.py`
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

## Exact Commands Used During This Analysis

### Task 101 live status

```bash
pdm run run-hemma -- pdm run task-101-pilot status \
  --launch-root /srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot/task101-20260313t102144z
```

### Live launch metadata

```bash
pdm run run-hemma -- /bin/bash -lc \
  'cat /srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot/task101-20260313t102144z/launch.json'
```

### Live container logs

```bash
pdm run run-hemma -- /bin/bash -lc \
  'sudo docker logs --tail 200 task101-20260313t102144z-container 2>&1 | tail -n 200'
```

### Live checkpoint metadata

```bash
pdm run run-hemma -- /bin/bash -lc \
  'cat /srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/latest_checkpoint.json'
```

### Live checkpoint sizes

```bash
pdm run run-hemma -- /bin/bash -lc \
  'du -sh /srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/* | sort -h | tail -n 20'
```

### Live checkpoint directory names

```bash
pdm run run-hemma -- /bin/bash -lc \
  'find /srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints -maxdepth 1 -mindepth 1 -type d -printf "%f\n" | sort | tail -n 10'
```

### Search run root for TensorBoard or other live tracking artifacts

```bash
pdm run run-hemma -- /bin/bash -lc \
  'find /srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z -type f | grep -E "events|tensorboard|training_summary|report|failure|checkpoint-final|checkpoint-epoch"'
```

### Launch detached Task 116 resource monitor

```bash
pdm run run-hemma -- pdm run python -m \
  scripts.sir_convert_a_lot.devops.run_task116_hemma_resource_monitor \
  launch \
  --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-116-hemma-resource-monitor \
  --interval-seconds 15
```

### Inspect detached Task 116 resource monitor

```bash
pdm run run-hemma -- pdm run python -m \
  scripts.sir_convert_a_lot.devops.run_task116_hemma_resource_monitor \
  summary \
  --launch-root /srv/scratch/sir-convert-a-lot/build/verification/task-116-hemma-resource-monitor/task116-resource-20260313t135754z
```

## Live Run Metadata

The active Task 101 launch metadata recorded these effective settings:

```json
{
  "launch_id": "task101-20260313t102144z",
  "container_name": "task101-20260313t102144z-container",
  "pilot_bundle_root": "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h",
  "train_manifest_family": "swedish_pilot_train",
  "eval_manifest_family": "swedish_checkpoint_dev",
  "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
  "batch_size": 1,
  "lr": 2e-05,
  "num_epochs": 1000,
  "max_steps": 1000000,
  "checkpoint_interval_steps": 2,
  "durable_checkpoint_retention": 2,
  "durable_checkpoint_min_free_bytes": 17179869184
}
```

Additional live facts from status inspection:

- container status: `running`
- `oom_killed = false`
- started at: `2026-03-13T10:21:44.929427417Z`
- latest checkpoint at `2026-03-13T14:06:39Z`
- latest durable checkpoint step at the time of status capture: `666`
- train rows: `8445`
- eval rows: `8`

Derived wall-clock estimate from observed progress:

- roughly `666` optimizer-step increments over about `3.77` hours
- rough effective pace: about `176-180` recorded steps per hour

This is not a throughput claim about useful compute. It is only the pace of
the currently recorded step counter.

## Live Loss Evidence

### Raw stdout-derived loss tail

At `2026-03-13T14:07:47Z`, the live status surface exposed this tail:

```text
Epoch 0 | Step 580 | Loss: 7.9108
Epoch 0 | Step 590 | Loss: 6.7756
Epoch 0 | Step 600 | Loss: 6.6522
Epoch 0 | Step 610 | Loss: 6.6306
Epoch 0 | Step 620 | Loss: 6.8178
Epoch 0 | Step 630 | Loss: 6.6650
Epoch 0 | Step 640 | Loss: 6.2899
Epoch 0 | Step 650 | Loss: 6.4669
Epoch 0 | Step 660 | Loss: 6.8474
```

The complete live series observed during this analysis ran from `Step 10` to
`Step 660`.

### Smoothed loss view

To approximate a more classical training-curve interpretation from the
available stdout-only signal, a trailing moving average over `5` logged points
and an EMA (`alpha = 0.2`) were computed from the captured step-loss pairs:

```text
step   raw     MA(5)   EMA(0.2)
10     13.53   13.53   13.53
50      8.10    9.59   10.57
100     7.70    8.01    8.81
150     7.54    7.52    7.95
200     7.39    7.34    7.55
250     6.99    6.99    7.15
300     6.39    6.99    7.00
350     6.68    6.91    6.90
400     6.86    6.82    6.86
450     5.71    6.51    6.54
500     7.26    6.92    6.83
550     6.74    6.92    6.87
600     6.65    7.01    6.94
650     6.47    6.57    6.67
660     6.85    6.71    6.71
```

Compact sparkline view:

```text
raw      █▄▄▃▃▃▃▃▃▃▃▂▃▂▃▂▃▃▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▁▂▂▂▂▂▂▂▂▂▂▂▂▃▂▂▂▂▂▂
smoothed █▆▅▄▄▃▃▃▃▃▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▁▂▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▂▁▂▂▁▁▁▂▂▂▂▁▁▁
```

Interpretation:

- the raw loss is visibly noisy,
- the smoothed curve still trends downward,
- and the observed behavior does not currently look like divergence.

The current live loss picture therefore supports:

- ongoing learning,
- weak observability,
- and a monitoring deficit,

not an immediate optimizer failure.

## Live Resource Monitoring Evidence

The detached Task 116 resource monitor was not launched by default as part of
the Task 101 runtime. It was started manually during this analysis.

Launch metadata:

```json
{
  "generated_at": "2026-03-13T13:57:54Z",
  "launch_id": "task116-resource-20260313t135754z",
  "runtime_kind": "rocm",
  "interval_seconds": 15.0
}
```

Summary over `41` samples from `2026-03-13T13:57:54Z` to
`2026-03-13T14:08:02Z`:

```json
{
  "launch_id": "task116-resource-20260313t135754z",
  "sample_count": 41,
  "first_sample_at": "2026-03-13T13:57:54Z",
  "last_sample_at": "2026-03-13T14:08:02Z",
  "gpu_busy_percent_min": 3,
  "gpu_busy_percent_median": 5.0,
  "gpu_busy_percent_max": 12,
  "gpu_memory_used_percent_min": 68,
  "gpu_memory_used_percent_median": 68.0,
  "gpu_memory_used_percent_max": 68,
  "host_cpu_busy_percent_min": 3,
  "host_cpu_busy_percent_median": 4.0,
  "host_cpu_busy_percent_max": 15,
  "host_memory_used_percent_min": 38,
  "host_memory_used_percent_median": 39.0,
  "host_memory_used_percent_max": 41
}
```

Representative early samples:

```json
{"captured_at": "2026-03-13T13:57:54Z", "gpu_busy_percent": 6, "gpu_memory_used_percent": 68, "host_cpu_busy_percent": 15, "host_memory_used_percent": 38, "runtime_kind": "rocm"}
{"captured_at": "2026-03-13T13:58:10Z", "gpu_busy_percent": 6, "gpu_memory_used_percent": 68, "host_cpu_busy_percent": 5, "host_memory_used_percent": 38, "runtime_kind": "rocm"}
{"captured_at": "2026-03-13T13:58:25Z", "gpu_busy_percent": 5, "gpu_memory_used_percent": 68, "host_cpu_busy_percent": 4, "host_memory_used_percent": 40, "runtime_kind": "rocm"}
{"captured_at": "2026-03-13T13:58:40Z", "gpu_busy_percent": 9, "gpu_memory_used_percent": 68, "host_cpu_busy_percent": 4, "host_memory_used_percent": 40, "runtime_kind": "rocm"}
{"captured_at": "2026-03-13T13:58:55Z", "gpu_busy_percent": 3, "gpu_memory_used_percent": 68, "host_cpu_busy_percent": 3, "host_memory_used_percent": 40, "runtime_kind": "rocm"}
```

Interpretation:

- the model is resident in GPU memory,
- VRAM usage is steady and substantial,
- but actual GPU busy percentage is extremely low for a serious training run.

This is the strongest live evidence in this report. It converts “the GPU feels
underused” into a measured claim.

## Live Checkpoint and Artifact Evidence

The latest checkpoint metadata at one inspection point was:

```json
{
  "checkpoint_path": "/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00000666",
  "saved_at": "2026-03-13T14:06:39Z",
  "reason": "interval",
  "optimizer_steps_completed": 666,
  "epoch": 0,
  "next_epoch": 0,
  "next_step_in_epoch": 666
}
```

Checkpoint directory sizes:

```text
11G  .../checkpoints/state-step-00000666
11G  .../checkpoints/state-step-00000668
```

Checkpoint directory names at another probe point:

```text
.state-step-00000670.incomplete
state-step-00000666
state-step-00000668
```

Interpretation:

- the incomplete directory indicates the staging-save pattern from the recent
  checkpoint hardening work is active,
- retained checkpoint count is correctly bounded at `2`,
- but the interval is so aggressive that the run is continuously writing
  extremely large durable states.

This is likely a meaningful wall-clock throughput tax.

## Live Artifact Inventory Findings

The live run root currently contains:

```text
checkpoints/
latest_checkpoint.json
status.json
```

A search for these live artifacts returned no results during the run:

- TensorBoard event files
- explicit tracker output directories
- `training_summary.json`
- `report.json`
- `failure.txt`
- epoch checkpoint export directories
- final exported checkpoint directories

Interpretation:

- terminal artifacts are expected to appear only at completion or failure,
- but tracker artifacts should already exist if the TensorBoard integration were
  truly active.

This strongly suggests that the `Accelerator(log_with="tensorboard")` wiring is
incomplete and not enough by itself to produce useful live scalar monitoring.

## Code-Grounded Current Runtime Behavior

### Trainer tracking path is half-wired

The patched trainer constructs:

- `Accelerator(gradient_accumulation_steps=4, mixed_precision="bf16", log_with="tensorboard", project_dir=...)`

in `scripts/devops/qwen_finetuning_patches/sft_12hz.py`.

However, during this analysis:

- no TensorBoard event files were found in the live run root,
- no explicit `accelerator.init_trackers(...)` use was observed,
- and no `accelerator.log(...)` calls were present in the inspected training
  path.

Interpretation:

- tracking intent exists,
- but the usable tracking surface does not.

### The logged loss is raw and composite

The live stdout loss comes directly from:

- `loss = outputs.loss + 0.3 * sub_talker_loss`
- `accelerator.print(f"Epoch {epoch} | Step {step} | Loss: {loss.item():.4f}")`

This means the visible loss is:

- unsmoothed,
- logged only every `10` steps,
- and combines two training objectives.

That is sufficient for a rough smoke signal, but not for a classical training
dashboard.

### The dataloader path is highly likely to starve the GPU

The current dataset implementation still does the following per sample inside
`scripts/devops/qwen_finetuning_patches/dataset.py`:

- `librosa.load(path, sr=None, mono=True)` inside `_load_audio_to_np(...)`
- `mel_spectrogram(...)` inside `extract_mels(...)`
- both are called from `__getitem__(...)`

The current `DataLoader` construction in
`scripts/devops/qwen_finetuning_patches/sft_12hz.py` does not pass:

- `num_workers`
- `pin_memory`
- `persistent_workers`
- `prefetch_factor`

This is a direct code-level explanation for the live monitor evidence:

- GPU memory resident,
- low GPU busy,
- low host CPU median at the sample resolution,
- and step progression that is too slow for a 1.7B model that is already loaded.

Important nuance:

- the low host CPU median does not prove the dataloader is innocent,
- because short decode / mel bursts can be missed by a `15` second sampler,
- and a single-threaded data path can still starve the GPU while looking quiet
  in low-frequency host snapshots.

### Status is not a true live heartbeat

The probe writes a running-status payload before training starts, but the
running payload only captures launch-time data such as:

- `status = "running"`
- `updated_at`
- manifest paths
- row counts
- checkpoint policy

No mid-run update path was observed for:

- current step
- current epoch
- current loss
- smoothed loss
- last checkpoint step
- last checkpoint timestamp
- throughput

That is why `pilot_status.updated_at` stayed anchored to startup time during
the live run.

### The monitor exists, but Task 101 does not activate it by default

The committed Task 116 monitor surfaces are real and working:

- `scripts/sir_convert_a_lot/devops/run_task116_hemma_resource_monitor.py`
- `scripts/sir_convert_a_lot/devops/task116_hemma_resource_monitor_runtime.py`
- `scripts/sir_convert_a_lot/infrastructure/gpu_utilization_snapshot.py`

However, no Task 101 runtime code references to Task 116 were found during
this analysis.

Interpretation:

- resource monitoring is possible,
- but it is still an operator opt-in rather than a default pilot behavior.

## Confirmed Robust and Working Surfaces

The following surfaces are currently working and should be treated as
off-limits for the next optimization slice unless new evidence forces a
different conclusion.

### Detached Hemma launch architecture

The detached Task 101 launch architecture is working:

- the container is launched detached,
- the client session is not required to keep the run alive,
- metadata is persisted under scratch-backed run roots,
- and the CLI can inspect the detached state after launch.

Do not replace this with attached shell execution or ad hoc SSH sessions.

### Deterministic pilot bundle ownership

The live run is correctly using the deterministic pilot bundle root rather than
the generic promoted preprocessing root.

Do not regress this back into ad hoc subset selection or generic corpus-root
training.

### Durable checkpoint staging and bounded retention

The recent checkpoint hardening work is functioning:

- durable saves use a staging directory pattern,
- retention is bounded,
- live metadata points at the latest durable checkpoint,
- and current checkpoint rotation is behaving as designed.

Do not rip out the checkpoint staging / compatibility / retention logic while
addressing throughput. The problem is the interval policy, not the existence of
durable checkpoints.

### Containerized ROCm runtime

The training lane is correctly containerized and ROCm-visible:

- the model is resident in VRAM,
- the container remains healthy,
- and the run is progressing without OOM termination.

Do not collapse the training lane back into raw-host training processes.

### Multi-speaker base-model patch direction

The current base-model lane intentionally preserves:

- base-model conditioning through `speaker_encoder`,
- and the known text-projection fix in the patched Qwen path.

This report found no live evidence that those changes are the current
bottleneck. Do not make speculative architectural reversions in that area while
the real bottlenecks are still observability and throughput.

### Train-only loop with explicit eval-manifest recording

The system currently truthfully records the held-out eval manifest in launch
and status artifacts while remaining train-only at runtime.

That limitation is real, but it is also currently contract-correct.

Do not silently add in-training eval inside a performance or monitoring task.
If the team wants that capability, it should land as an explicit new contract.

## Confirmed Issues

### 1. GPU is severely underutilized

Confirmed by live Task 116 evidence:

- median GPU busy `5%`
- max GPU busy `12%`
- median GPU memory used `68%`

This is the single most important operational issue observed.

### 2. Durable checkpoint cadence is much too aggressive for a convergence run

Confirmed by live launch settings and live checkpoint sizes:

- checkpoint interval: every `2` steps
- each retained durable checkpoint: about `11G`
- current retained directories plus in-progress staging:
  - `state-step-00000666`
  - `state-step-00000668`
  - `.state-step-00000670.incomplete`

This is almost certainly creating heavy scratch I/O overhead.

### 3. Live training monitoring is insufficient

Confirmed by run-root inspection:

- no TensorBoard event files found,
- no other live scalar-tracking artifact found,
- only raw stdout loss and checkpoint metadata are usable during the run.

### 4. `status.json` is not a true live progress surface

Confirmed by status payload inspection:

- `updated_at` remains near launch time,
- no current step or smoothed loss is persisted mid-run.

### 5. Logs are too noisy for operational diagnosis

Confirmed by container-log inspection:

- MIOpen workspace warnings repeatedly interleave with loss logs,
- making it harder to read progress and detect real anomalies.

### 6. The current dataloader path is structurally weak for throughput

Confirmed by code inspection:

- audio load in `__getitem__`
- mel extraction in `__getitem__`
- no explicit `DataLoader` worker / prefetch tuning

The live GPU-utilization evidence is consistent with this weakness.

### 7. The active run has weak observability around step semantics

Confirmed by code inspection:

- `gradient_accumulation_steps = 4`
- but the visible live counters and checkpoint cadence are keyed to the current
  increment surface named `optimizer_steps_completed`

This report does not prove a functional bug, but the naming and semantics are
ambiguous enough that operators cannot easily reason about true optimizer
updates versus loop iterations.

### 8. The current live monitoring story is partly hidden in detached helper code

Confirmed by runtime shape:

- the resource monitor is a committed surface,
- but not a default Task 101 behavior,
- so the operator has to know it exists and remember to start it.

## High-Confidence Inferences

These statements are not proven to theorem-level certainty, but the current
evidence supports them strongly.

### The pipeline is likely bottlenecked more by data / I/O orchestration than by pure GPU compute

Why this inference is strong:

- GPU busy is low,
- VRAM is stable and substantial,
- the dataloader path is expensive and single-threaded by default,
- and checkpoint cadence is extremely aggressive.

### Checkpoint I/O is probably a meaningful contributor to low throughput

Why this inference is strong:

- the run saves durable state every `2` steps,
- each state is about `11G`,
- and the run is continuously cycling very large checkpoint directories.

### It is too early to tune optimizer hyperparameters based on the current evidence

Why this inference is strong:

- the smoothed loss still trends downward,
- there is no live eval signal,
- and the throughput / observability defects are much more obvious than any
  optimizer defect.

## Deliberate Limitations That Should Be Called Out, Not “Fixed by Accident”

These are not hidden bugs. They are current contract boundaries.

### No in-training evaluation

The upstream patched trainer is still train-only.

Implication:

- the team can say “training loss is decreasing,”
- but cannot yet say “generalization quality is improving” from this live lane
  alone.

### Task 116 is not yet default-wired into Task 101 launches

The monitoring capability exists, but operator discipline is still required.

### The current report and training summary are terminal artifacts

`report.json` and `training_summary.json` are completion-time surfaces, not live
monitoring surfaces.

That is fine as a contract, but it does not solve active-run observability.

## Relevant Log Excerpts

### Training progress excerpt

```text
Epoch 0 | Step 300 | Loss: 6.3898
Epoch 0 | Step 310 | Loss: 7.2376
Epoch 0 | Step 320 | Loss: 6.8166
Epoch 0 | Step 330 | Loss: 7.1815
Epoch 0 | Step 340 | Loss: 6.6139
Epoch 0 | Step 350 | Loss: 6.6794
Epoch 0 | Step 360 | Loss: 6.8136
Epoch 0 | Step 370 | Loss: 6.6061
Epoch 0 | Step 380 | Loss: 7.0121
Epoch 0 | Step 390 | Loss: 6.8221
Epoch 0 | Step 400 | Loss: 6.8583
Epoch 0 | Step 410 | Loss: 6.8700
Epoch 0 | Step 420 | Loss: 6.7377
Epoch 0 | Step 430 | Loss: 6.7722
Epoch 0 | Step 440 | Loss: 6.4446
Epoch 0 | Step 450 | Loss: 5.7130
Epoch 0 | Step 460 | Loss: 6.6248
Epoch 0 | Step 470 | Loss: 6.9918
Epoch 0 | Step 480 | Loss: 6.6625
Epoch 0 | Step 490 | Loss: 7.0350
Epoch 0 | Step 500 | Loss: 7.2633
Epoch 0 | Step 510 | Loss: 6.9496
Epoch 0 | Step 520 | Loss: 6.7901
Epoch 0 | Step 530 | Loss: 7.2971
Epoch 0 | Step 540 | Loss: 6.8117
Epoch 0 | Step 550 | Loss: 6.7369
Epoch 0 | Step 560 | Loss: 6.7082
Epoch 0 | Step 570 | Loss: 6.9830
Epoch 0 | Step 580 | Loss: 7.9108
Epoch 0 | Step 590 | Loss: 6.7756
Epoch 0 | Step 600 | Loss: 6.6522
Epoch 0 | Step 610 | Loss: 6.6306
Epoch 0 | Step 620 | Loss: 6.8178
Epoch 0 | Step 630 | Loss: 6.6650
Epoch 0 | Step 640 | Loss: 6.2899
Epoch 0 | Step 650 | Loss: 6.4669
Epoch 0 | Step 660 | Loss: 6.8474
```

### MIOpen warning excerpt

```text
MIOpen(HIP): Warning [IsEnoughWorkspace] [GetSolutionsFallback WTI] Solver <GemmFwdRest>, workspace required: 996480, provided ptr: 0 size: 0
MIOpen(HIP): Warning [IsEnoughWorkspace] [EvaluateInvokers] Solver <GemmFwdRest>, workspace required: 996480, provided ptr: 0 size: 0
...
MIOpen(HIP): Warning [IsEnoughWorkspace] [GetSolutionsFallback WTI] Solver <GemmFwdRest>, workspace required: 797568, provided ptr: 0 size: 0
MIOpen(HIP): Warning [IsEnoughWorkspace] [EvaluateInvokers] Solver <GemmFwdRest>, workspace required: 797568, provided ptr: 0 size: 0
```

Interpretation:

- these warnings do not by themselves prove correctness failure,
- but they are persistent enough to deserve a performance-focused follow-up.

## What This Report Does Not Yet Prove

This report does not yet prove:

- whether `batch_size = 2` fits safely and improves effective throughput,
- how much of the throughput loss comes from checkpoint I/O versus dataloader
  starvation,
- whether precomputing `ref_mel` is the best fix versus first trying dataloader
  workers and cache strategy,
- or whether the MIOpen workspace warnings materially affect training speed.

Those should be answered by a bounded profiling / optimization task, not by
intuition.

## Recommended Next-Slice Boundaries

The next slice should focus on observability and throughput, not on new model
behavior.

### Safe first changes

- wire real tracker initialization and scalar logging through Accelerate
- persist a live heartbeat status surface with:
  - current step
  - current epoch
  - last raw loss
  - EMA / moving-average loss
  - last checkpoint step
  - last checkpoint timestamp
  - effective throughput
- make the Task 116 resource monitor default-on for long Task 101 launches, or
  make it one explicit sibling command emitted by launch output
- reduce durable checkpoint interval for future convergence runs from `2` to
  something like `50` or `100`
- profile the dataloader path before changing training math

### Now-decisioned target posture

The follow-on story created from this report must treat these as the operative
performance targets:

- `>= 90%` steady-state median GPU busy as the acceptance gate
- `> 95%` steady-state median GPU busy as the preferred end state
- `1.0` second or finer GPU sampling for any run used as saturation evidence
- phase-aware evidence that excludes checkpoint windows from the canonical
  steady-state gate

### Changes that should not be bundled into that slice

- do not redesign the detached launcher architecture
- do not redesign deterministic pilot-bundle ownership
- do not redesign durable checkpoint compatibility or staging
- do not silently add in-training evaluation
- do not tune learning rate or other core optimizer settings first

## Relevant Established Tooling References

The current repo already ships `tensorboard` in the Qwen training image:

- `containers/qwen-finetune-hemma/requirements.txt`

Relevant official documentation for the next observability slice:

- Hugging Face Accelerate experiment trackers:
  - <https://huggingface.co/docs/accelerate/en/usage_guides/tracking>
  - documents `Accelerator.init_trackers(...)` and `Accelerator.log(...)`
- MLflow tracking:
  - <https://mlflow.org/docs/latest/ml/tracking/>
  - provides run tracking for params, metrics, artifacts, and comparison UI
- MLflow system metrics:
  - <https://mlflow.org/docs/latest/ml/tracking/system-metrics/>
  - explicitly documents CPU / memory / GPU system metrics logging and notes
    AMD/HIP support via `pyrsmi`
- PyTorch profiler:
  - <https://docs.pytorch.org/tutorials/recipes/recipes/profiler_recipe.html>
  - should be used for bounded profiling windows rather than permanent
    long-run telemetry

## Bottom Line

The current Task 101 run is alive, learning, and operationally stable, but it
is not a well-instrumented training pipeline yet.

The strongest evidence in this report is not the noisy loss. It is the
combination of:

- very low measured GPU busy,
- huge and extremely frequent durable checkpoint writes,
- on-demand per-sample audio decode and mel extraction,
- and missing live tracker artifacts despite nominal TensorBoard wiring.

That combination makes the next priority clear:

- improve observability,
- remove throughput bottlenecks,
- and only then revisit training-program tuning if the learning curves still
  justify it.
