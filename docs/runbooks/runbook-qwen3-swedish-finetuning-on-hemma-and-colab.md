---
type: runbook
id: RUN-qwen3-swedish-finetuning-on-hemma-and-colab
title: Qwen3-TTS Swedish Finetuning Runbook for Hemma and Colab
status: active
created: 2026-03-08
updated: 2026-03-15
owners:
  - platform
system: hemma.hule.education
tags:
  - qwen
  - tts
  - finetuning
  - swedish
  - hemma
  - colab
links:
  - .agents/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-27-transition-to-domain-centric-ml-pipeline-structure.md
  - docs/backlog/tasks/task-181-add-real-in-training-held-out-eval-loop-to-task-101-qwen-training.md
---

## Purpose

Define the canonical Sir Convert-a-Lot workflow for planning and eventually
running Swedish `Qwen/Qwen3-TTS-12Hz-1.7B-Base` fine-tuning on the real Hemma
ROCm host and on Google Colab H100, using the domain-centric ML architecture.

## Ground Truth

This runbook is intentionally anchored to these truth surfaces:

- Repo governance and operations:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
  - `docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md`
- ML Domain Root:
  - `scripts/sir_convert_a_lot/ml/qwen/`
- CLI Entrypoints:
  - `scripts/sir_convert_a_lot/cli/ml/`

## What We Are Actually Trying To Do

The target is:

- `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
- full fine-tuning objective
- Swedish language expansion
- multi-speaker training/evaluation discipline
- containerized Hemma runtime as the default training and scale lane

## Non-Negotiables

- Use containers, never raw host `systemd` training.
- Use domain-centric commands:
  - `pdm run qwen-train launch`
  - `pdm run qwen-preprocess`
- Keep training runtimes isolated from the main service image.
- Preserve canonical persistent cache roots on Hemma.

## Frozen Pilot Dataset Rule

The current canonical pilot-owned preprocessing source is:

- `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`

Training must use a deterministic training bundle projected from this root.

## Current Runtime Separation

Use the current repo surfaces as two different lanes:

1. Existing Qwen serving/benchmark lane:
   - `scripts/sir_convert_a_lot/cli/ml/qwen_benchmarks.py`
   - `vllm/vllm-omni-rocm`
1. New Qwen fine-tuning lane:
   - `scripts/sir_convert_a_lot/ml/qwen/training/`
   - dedicated training runtime (`ml.qwen.common.runtime`)

## Runtime-Model

The containerized Qwen runtime is canonical for preprocessing and training.
The Hemma host is for orchestration only.

- `pdm run qwen-preprocess` dispatches to the detached stage orchestrator.
- Immutable scratch-backed run roots are mandatory for all preprocessing runs.

## Training Lane Direction

- Hemma is the default training lane for bounded pilot work and scale-up.
- Colab remains an optional fallback or comparison lane.

## Current Saturation Evidence (2026-03-13)

Bounded Story 26 evidence currently shows:

- `task161-20260313t212725z-cache-off`: steady-state train GPU median `26%`
- `task161-20260313t212725z-cache-on`: steady-state train GPU median `8%`
- `task162-20260313t220644z-profile`: steady-state train GPU median `3%`
- all three runs reported `ref_mel_cache` stats as
  `cache_hits=0`, `cache_misses=0`, `cache_size=0`
- `task162` ROCm attribution:
  - HIP API `98.74s`
  - kernels `102.08s`
  - memory copy `1.73s`
  - top HIP API calls:
    `hipLaunchKernel=44.18s`, `hipMemcpyWithStream=21.52s`,
    `hipEventSynchronize=17.89s`

Operational interpretation:

- the current lane is host-orchestration/synchronization bound
- runtime `ref_mel` cache should not be treated as a proven saturation lever
- persistent `NaN` loss is a quality blocker; no saturation acceptance should
  be claimed from a run with unfixed `NaN` training state

## Held-Out Eval Posture

The Task 101 lane already carries the held-out `swedish_checkpoint_dev`
manifest through launch metadata, status, and terminal reports. That contract
is no longer sufficient for long pilot runs.

Current implementation truth after the `T181` eval slice lands locally:

- the held-out eval manifest exists and is required,
- the inner patched Qwen trainer prepares a real eval dataset and dataloader
  from `--eval-jsonl`,
- bounded in-training held-out eval runs at explicit optimizer-step cadence,
- and eval loss now persists into trackers, live status, and terminal reports.

The next required proof is operational rather than contractual:

- run one short bounded Hemma launch with the real eval loop enabled,
- confirm `status.json` and `report.json` carry live and terminal eval fields,
- then promote the eval loop into the longer pilot lane.

Follow-on control posture after `T182`:

- use `qwen-train eval` for standalone checkpoint eval against explicit held-out
  material when we want a real check without rebuilding the full pilot bundle,
- and use the schedule runner for planned
  `train -> stop -> eval -> resume` cadence around durable checkpoints.

## Shard and Work Allocation

Future incremental allocation has a strict canonical path:

- dedupe completed run roots into one canonical processed root
- build one immutable shard registry from the remaining universe
- issue worker processing units only from shard ids

Canonical commands:

- `pdm run qwen-canonical-root build`
- `pdm run qwen-shard build-registry`
- `pdm run qwen-shard issue-unit`

## Dependency Baseline

Qwen training image baseline:

- `qwen_tts`
- ROCm-compatible `torch`
- `accelerate`, `transformers`, `flash_attn`

Canonical runtime assets:

- `containers/qwen-finetune-hemma/Dockerfile`
- `scripts/sir_convert_a_lot/ml/qwen/training/trainer_smoke_probe.py`

Wrapper-driven Hemma smoke command:

```bash
pdm run run-hemma -- pdm run qwen-smoke
```

Preprocessing/eval baseline:

- `datasets`, `jiwer`, `librosa`, `soundfile`

Canonical repo surface for the preprocessing lane:

- install: `pdm install -G qwen-preprocessing`
- run: `pdm run qwen-preprocess`
- runner: `scripts/sir_convert_a_lot/cli/ml/qwen_preprocess.py`

## Execution Order (New Posture)

1. **Verify Infrastructure:**
   - `pdm run run-hemma -- pdm run qwen-smoke`
1. **Source Selection:**
   - `pdm run qwen-preprocess --stage source-selection --source-mode staged-public-corpus`
1. **Row Processing (Detached):**
   - `pdm run qwen-preprocess --stage row-processing --row-worker-count 4`
1. **Finalization (GPU-backed):**
   - `pdm run qwen-preprocess --stage finalization`
1. **Bundle Materialization:**
   - `pdm run qwen-bundle build`
1. **Training Launch:**
   - `pdm run qwen-train launch`
1. **Status Inspection:**
   - `pdm run qwen-train status`

## Fault-Tolerant Resume

- Scheduled Task 101 runs use this canonical control posture:
  - durable checkpoint every `500` optimizer steps
  - held-out eval every `100` optimizer steps
  - retain newest `3` durable trainer-state checkpoints
  - force one durable checkpoint at epoch end before resume/eval decisions
- Latest durable step is recorded in `latest_checkpoint.json`.
- Schedule-driven resumes advance the canonical latest detached launch pointer,
  so pointerless `qwen-train status` and `qwen-train stop` target the resumed
  launch rather than the earlier stopped source launch.
- Schedule control fails closed when checkpoint, eval-manifest, or bundle-root
  paths escape the mounted scratch root or are missing from disk.
- Resume with: `pdm run qwen-train resume`.

## Hemma Storage Tiers

- SSD work tier: `/srv/scratch` (Builds, caches, active training).
- HDD bulk-data tier: `/srv/storage` (Raw corpora, frozen roots).
- OS disk: `/` (Avoid for ML artifacts).
