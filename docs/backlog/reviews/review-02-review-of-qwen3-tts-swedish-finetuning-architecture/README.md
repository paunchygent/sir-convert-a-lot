---
id: review-02-review-of-qwen3-tts-swedish-finetuning-architecture
title: Review of Qwen3-TTS Swedish Finetuning Architecture
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

## Review Scope

Honest, objective code review of the Qwen3-TTS Swedish fine-tuning architecture, assessed against `AGENTS.md` golden rules and the `runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md` operational constraints.

The scope covers:

- Command runners: `run_task100_hemma_qwen_finetune_smoke.py`, `run_task101_hemma_qwen_pilot.py`
- Detached runtime orchestrators: `task100_qwen_finetune_runtime.py`, `task101_qwen_pilot_runtime.py`
- Container definitions: `containers/qwen-finetune-hemma/Dockerfile`
- Internal probes & training loops: `task101_qwen_pilot_probe.py`, `sft_12hz.py`, `dataset.py`

## Findings: Strengths (What Went Right)

The architecture fundamentally respects the repo's strict operational boundaries, successfully avoiding raw Jupyter notebooks or mutated host environments.

1. **Strict Containerization & Isolation:** Building a dedicated `task100` image and executing exclusively via `docker run` guarantees no pollution of the Hemma host's Python environment.
1. **Storage Tier Discipline:** Accurately respects the Hemma SSD (`/srv/scratch`) vs HDD (`/srv/storage`) policies. `MountResolution` dynamically maps canonical roots and fallback home mounts flawlessly.
1. **Detached Execution Enforcement:** Task 101 perfectly implements the detached orchestration mandate. It writes PID/container details to `launch.json` and allows `--status` checks without a persistent SSH session.
1. **Flawless Resume Mechanics:** `sft_12hz.py` handles `resume_step_in_epoch` using `accelerator.skip_first_batches` cleanly. The `latest_checkpoint.json` paired with `accelerator.save_state` gives a highly resilient preemptible training environment.
1. **Strict Provenance & Deterministic Artifacts:** Dumping `status.json`, `report.json`, and `training_summary.json` with exact dependency metrics eliminates the mystery of "which run produced this checkpoint".

## Findings: Architectural Risks (Deep Dive)

### 1. Severe Dataloader I/O Bottleneck (`dataset.py`)

In `dataset.py:184-203`, `__getitem__` dynamically loads raw audio using `librosa.load` and runs a full Mel-spectrogram extraction on the CPU for **every single batch item, every epoch**.

- **Risk:** At scale, GPU utilization will plummet because it will be starved waiting for CPU-bound disk I/O and librosa decoding. This negates the benefit of `flash_attention_2`.
- **Recommendation:** Move Mel-spectrogram extraction to the preprocessing pipeline (`task103`) and save them as `.pt` or `.npy` files. The dataloader should only load pre-computed tensors.
- **Evidence:** [`evidence-01-dataset-io-bottleneck.md`](./evidence-01-dataset-io-bottleneck.md)

### 2. Ungraceful Detached Shutdown (`task101_qwen_pilot_runtime.py` & `sft_12hz.py`)

`stop_detached_pilot` uses `docker stop`, which sends a `SIGTERM` to the container and waits 10 seconds before sending `SIGKILL`.

- **Risk:** `sft_12hz.py` has no signal handlers. If preempted, the Python process dies immediately. Any progress since the last `checkpoint_interval_steps` is permanently lost.
- **Recommendation:** Add a `signal.signal(signal.SIGTERM, ...)` handler in `sft_12hz.py` that sets a `stop_requested = True` flag. Invoke `_save_durable_checkpoint` and exit cleanly before the SIGKILL.
- **Evidence:** [`evidence-02-ungraceful-shutdown.md`](./evidence-02-ungraceful-shutdown.md)

### 3. Dangerous Synchronous Cache Copying

In `task100_qwen_finetune_runtime.py`, `_sync_home_cache_into_data_disk` iterates through directories and executes `cp -a` synchronously via `subprocess.run`.

- **Risk:** Hugging Face caches for a 1.7B parameter model can exceed 50GB. This loop blocks execution silently for a significant amount of time and cannot safely resume partial transfers.
- **Recommendation:** Use `rsync -a` natively to handle incremental transfers safely rather than a Python `for`-loop wrapping `cp`.
- **Evidence:** [`evidence-03-synchronous-cache-copy.md`](./evidence-03-synchronous-cache-copy.md)

### 4. Hardcoded ROCm Lock-in Blocks Colab H100 (`Dockerfile`)

Your runbook states: *"Colab H100 only as an optional fallback or comparison lane"*. However, the `Dockerfile` heavily hardcodes AMD specifics (`rocm/dev-ubuntu`, `GPU_ARCHS=gfx1201`).

- **Risk:** This image is absolutely unusable on Colab's Nvidia H100 instances. The Hemma-to-Colab migration path will completely break at the container level.
- **Recommendation:** Create a multi-arch builder pattern, or maintain a separate `Dockerfile.cuda` in tandem for the Colab scaling lane.
- **Evidence:** [`evidence-04-hardcoded-rocm.md`](./evidence-04-hardcoded-rocm.md)

### 5. Coupling `buildx` Execution With Runtime Launch

`ensure_image_present` triggers a `docker buildx build` directly during the `launch` pipeline.

- **Risk:** The Dockerfile clones and compiles `flash-attention` from source. On a cache miss, the `pdm run task-101-pilot launch` command will stall for 30–45 minutes compiling C++/CUDA/HIP bindings before launching.
- **Recommendation:** Separate the image build phase from the execution phase, or emit highly visible warnings to the console when a compilation build is triggered.

### 6. Deeply Nested `SystemExit` Calls

Helpers like `_required_str` and `_load_latest_checkpoint` use `raise SystemExit("...")` on failure deep within runtime logic.

- **Risk:** These make unit testing nearly impossible and prevent calling functions from catching errors to trigger fallbacks.
- **Recommendation:** Raise custom exceptions (e.g., `MetadataParseError`) and catch them in `main()` to trigger the `SystemExit`.

### 7. Hardcoded Constants in Loss Function (`sft_12hz.py`)

In `sft_12hz.py:460`: `loss = outputs.loss + 0.3 * sub_talker_loss`

- **Risk:** The `0.3` weight is hardcoded. If the multi-speaker expansion requires tuning the sub-talker vs main-talker loss balance, it cannot be configured via CLI.
- **Recommendation:** Expose this as a configurable parameter (`--sub_talker_loss_weight`) in `train_with_args`.

## Decision

The system architecture (Docker isolation, strict paths, detached processes) is exceptional and perfectly aligned with governance docs. The code architecture and ML pipeline, however, require resilience hardening (SIGTERM handling, cache syncing) and performance optimization (pre-computing Mel-spectrograms) before scaling beyond the initial pilot.

## Response

This review is accepted as the baseline for the next set of hardening tasks.

## Follow-up Actions

- [ ] Extract Mel-spectrogram computation from `dataset.py` into the `task103` preprocessing pipeline.
- [ ] Add `SIGTERM` handling to `sft_12hz.py` for graceful durable checkpointing on `docker stop`.
- [ ] Replace synchronous `cp -a` in `_sync_home_cache_into_data_disk` with `rsync`.
- [ ] Establish a `Dockerfile.cuda` for the Colab fallback lane.
- [ ] Expose `--sub_talker_loss_weight` in the patched training script.
- [ ] Refactor deep `SystemExit` calls into custom exceptions in runtime utilities.

## Completion

Review documented and finalized.
