---
id: review-02-review-of-qwen3-tts-swedish-finetuning-architecture
title: Qwen3-TTS Swedish Finetuning Architecture Assessment
type: review
status: completed
priority: high
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
labels:
  - architecture-review
  - qwen-tts
  - finetuning
---
Structured review artifact for implementation or readiness checks.

## Review Scope

Honest, objective code review of the Qwen3-TTS Swedish fine-tuning architecture, assessed against `AGENTS.md` golden rules and the `runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md` operational constraints.

The scope covers:

- Command runners: `run_task100_hemma_qwen_finetune_smoke.py`, `run_task101_hemma_qwen_pilot.py`
- Detached runtime orchestrators: `task100_qwen_finetune_runtime.py`, `task101_qwen_pilot_runtime.py`
- Container definitions: `containers/qwen-finetune-hemma/Dockerfile`
- Internal probes & training loops: `task101_qwen_pilot_probe.py`, `sft_12hz.py`, `dataset.py`

## Findings

### Strengths (What Went Right)

The architecture fundamentally respects the repo's strict operational boundaries, successfully avoiding raw Jupyter notebooks or mutated host environments.

1. **Strict Containerization & Isolation:** Building a dedicated `task100` image and executing exclusively via `docker run` isolates the Hemma host's Python environment from the ML dependencies.
1. **Storage Tier Discipline:** Accurately maps the Hemma SSD (`/srv/scratch`) vs HDD (`/srv/storage`) policies. `MountResolution` dynamically handles canonical roots and fallback home mounts.
1. **Detached Execution Enforcement:** Task 101 successfully implements the detached orchestration mandate. It writes PID/container details to `launch.json` and allows `--status` checks without a persistent SSH session.
1. **Durable Resume Mechanics:** `sft_12hz.py` handles `resume_step_in_epoch` using `accelerator.skip_first_batches`. The `latest_checkpoint.json` paired with `accelerator.save_state` provides a strong foundation for a preemptible training environment, requiring only graceful shutdown handling to become fully robust.
1. **Strict Provenance & Deterministic Artifacts:** Dumping `status.json`, `report.json`, and `training_summary.json` with exact dependency metrics reduces the ambiguity of which run produced a given checkpoint.

### Architectural Risks (Deep Dive)

#### 1. Potential Dataloader I/O Bottleneck (`dataset.py`)

In `dataset.py:184-203`, `__getitem__` dynamically loads raw audio using `librosa.load` and runs a full Mel-spectrogram extraction on the CPU for **every single batch item, every epoch**.

- **Risk:** While directionally plausible as a CPU/I/O risk that could starve the GPU, the severity is not yet proven with live throughput evidence. Moving Mel-spectrogram extraction to the preprocessing pipeline would also materially change Task 103 artifact scope and storage cost.
- **Recommendation:** Profile dataloader throughput during the pilot. If GPU starvation is confirmed, consider moving Mel-spectrogram extraction to `task103` as a performance optimization.
- **Evidence:** [`ref-review-02-qwen-dataloader-io-bottleneck-evidence.md`](../../reference/ref-review-02-qwen-dataloader-io-bottleneck-evidence.md)

#### 2. Ungraceful Detached Shutdown (`task101_qwen_pilot_runtime.py` & `sft_12hz.py`)

`stop_detached_pilot` uses `docker stop`, which sends a `SIGTERM` to the container and waits before sending `SIGKILL`.

- **Risk:** `sft_12hz.py` originally had no signal handlers. If preempted, the Python process could die immediately. Any progress since the last `checkpoint_interval_steps` would be lost.
- **Recommendation:** Add explicit stop handling in `sft_12hz.py` so a requested stop can persist one final durable checkpoint before exit.
- **Evidence:** [`ref-review-02-qwen-ungraceful-detached-shutdown-evidence.md`](../../reference/ref-review-02-qwen-ungraceful-detached-shutdown-evidence.md)

#### 3. Dangerous Synchronous Cache Copying

In `task100_qwen_finetune_runtime.py`, `_sync_home_cache_into_data_disk` iterated through directories and executed `cp -a` synchronously via `subprocess.run`.

- **Risk:** Hugging Face caches for a `1.7B` parameter model can become very large. This loop blocks execution silently for a significant amount of time and cannot safely resume partial transfers.
- **Recommendation:** Use `rsync -a` natively to handle incremental transfers safely rather than a Python `for`-loop wrapping `cp`.
- **Evidence:** [`ref-review-02-qwen-synchronous-cache-copy-evidence.md`](../../reference/ref-review-02-qwen-synchronous-cache-copy-evidence.md)

#### 4. Missing Dockerfile for Colab H100 Fallback Lane (`Dockerfile`)

The current `Dockerfile` is intentionally Hemma/ROCm-specific (`rocm/dev-ubuntu`, `GPU_ARCHS=gfx1201`).

- **Risk:** While correct for the Hemma task surfaces, the runbook already treats Colab as a separate fallback/comparison lane. This image cannot be reused there.
- **Recommendation:** When activating the Colab lane, maintain a separate `Dockerfile.cuda` in tandem rather than attempting to compromise the current ROCm image.
- **Evidence:** [`ref-review-02-qwen-rocm-only-image-evidence.md`](../../reference/ref-review-02-qwen-rocm-only-image-evidence.md)

#### 5. Buildx Execution Blocks Cold-Cache Launch

`ensure_image_present` triggers a `docker buildx build` directly during the `launch` pipeline.

- **Risk:** While `run_task101_hemma_qwen_pilot.py` provides a `--skip-build` mitigation, executing a cold launch without this flag can block launch materially compiling C++/CUDA/HIP bindings.
- **Recommendation:** Emit highly visible warnings to the console when a compilation build is triggered to prevent perceived stalls during a cold launch.

#### 6. Tunability Debt: Hardcoded Constants in Loss Function (`sft_12hz.py`)

In `sft_12hz.py:460`: `loss = outputs.loss + 0.3 * sub_talker_loss`

- **Risk:** The `0.3` weight is hardcoded. This introduces tunability debt since the multi-speaker expansion may require adjusting the sub-talker vs main-talker loss balance via CLI.
- **Recommendation:** Expose this as a configurable parameter (`--sub_talker_loss_weight`) in `train_with_args` as a non-blocking optimization.

## Decision

The system architecture (Docker isolation, strict paths, detached processes) is well-aligned with governance docs. The code architecture and ML pipeline, however, require resilience hardening (SIGTERM handling, cache syncing) before scaling beyond the initial pilot. Parameter exposure and dataloader optimization should be treated as secondary improvements.

## Response

This review is accepted as the baseline for the next set of hardening tasks.

## Follow-up Actions

- [ ] Add `SIGTERM` handling to `sft_12hz.py` for graceful durable checkpointing on `docker stop`.
- [ ] Replace synchronous `cp -a` in `_sync_home_cache_into_data_disk` with `rsync`.
- [ ] Establish a `Dockerfile.cuda` when activating the Colab fallback lane.
- [ ] Profile dataloader throughput and evaluate moving Mel-spectrogram computation into the `task103` preprocessing pipeline.
- [ ] Expose `--sub_talker_loss_weight` in the patched training script.

## Completion

Review documented and finalized.

## Checklist

- [x] Scope reviewed
- [x] Findings recorded
- [x] Follow-up actions captured
