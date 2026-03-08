---
type: runbook
id: RUN-qwen3-swedish-finetuning-on-hemma-and-colab
title: Qwen3-TTS Swedish Finetuning Runbook for Hemma and Colab
status: active
created: 2026-03-08
updated: 2026-03-08
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
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-99-enable-triton-flash-attention-for-the-qwen-hemma-sidecar-benchmark.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison.md
  - docs/backlog/tasks/task-105-build-qwen3-tts-swedish-finetuning-research-repomix-package.md
  - docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-research-map-2026-03-08.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
  - https://github.com/QwenLM/Qwen3-TTS/tree/main/finetuning
  - https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html#amd-rocm
  - https://github.com/Dao-AILab/flash-attention
---

## Purpose

Define the canonical Sir Convert-a-Lot workflow for planning and eventually
running Swedish `Qwen/Qwen3-TTS-12Hz-1.7B-Base` fine-tuning on the real Hemma
ROCm host and on Google Colab H100, without collapsing into raw-host hacks,
single-speaker shortcuts, or undocumented notebook drift.

## Ground Truth

This runbook is intentionally anchored to these truth surfaces:

- Repo governance and operations:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
  - `docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md`
  - `docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md`
- Epic 08 planning:
  - `docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md`
  - `docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md`
  - `docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md`
- Official upstream model/runtime docs:
  - `QwenLM/Qwen3-TTS` model card and `finetuning/` README
  - official Qwen `prepare_data.py` and `sft_12hz.py`
  - official vLLM ROCm installation/runtime guidance
  - official `flash-attention` ROCm build/runtime guidance

## What We Are Actually Trying To Do

The target is not a one-speaker Swedish custom-voice adaptation.

The target is:

- `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
- full fine-tuning objective
- Swedish language expansion
- multi-speaker training/evaluation discipline
- containerized Hemma runtime first, Colab H100 scaling second

Important current upstream constraint:

- the public Qwen fine-tuning docs still describe a single-speaker training
  flow
- so the repo treats multi-speaker Swedish support as a planned engineering and
  evaluation lane on top of the official tooling, not as an already-settled
  upstream recipe

## Non-Negotiables

- Use docs-as-code first:
  - Epic 08 / Stories 24-25 / Tasks 99-104 are canonical.
- Use containers, never raw host `systemd` training.
- Use wrapper-driven Hemma commands:
  - `pdm run run-hemma -- <command> [args]`
- Keep training runtimes isolated from the main service image.
- Preserve canonical persistent cache roots on Hemma.
- Keep future serving outcomes downstream of ADR-0006 and ADR-0007.

## Current Proven Hemma Reality

Measured on the real Hemma GPU after first verifying the card was idle:

- GPU:
  - `AMD Radeon AI PRO R9700`
- total VRAM:
  - `32,061,259,776 B`
- clean idle baseline:
  - `59,936,768 B`
  - `No KFD PIDs currently running`

Real `Qwen3-TTS-1.7B` evidence already established:

- model residency only:
  - approximately `4.62 GB` total GPU usage in `rocm-smi`
- real official Swedish full-finetune step on Hemma:
  - actual Waxholm audio
  - actual Qwen `prepare_data.py`
  - actual Qwen `sft_12hz.py`
  - `AdamW`
  - real step reached with loss emitted
  - approximately `20.19 GB` total GPU usage in `rocm-smi`

Practical implication:

- Hemma is viable for bounded `1.7B` full-finetune pilot work
- the next work is about containerizing and scaling that path, not arguing that
  `32 GB` is too small

## Current Runtime Separation

Use the current repo surfaces as two different lanes:

1. Existing Qwen serving/benchmark lane:
   - `Task 79`
   - `Task 98`
   - `vllm/vllm-omni-rocm`
   - sidecar/serving proof
1. New Qwen fine-tuning lane:
   - Epic 08
   - Tasks 100-104
   - dedicated training runtime
   - full-finetune proof

Do not overload Task 79 into the full training runtime.

## Flash Attention Policy

For the current repo state:

- Triton flash attention is the canonical default for the Qwen Hemma benchmark
  lane again
- the older hardcoded disablement was a historical safety measure from the
  earlier RDNA4 bring-up phase
- one explicit disable switch may remain for regression triage only

Policy:

- default:
  - `VLLM_USE_TRITON_FLASH_ATTN=1`
- fallback:
  - disable only when triaging a concrete regression and record that fact in
    the benchmark output

This runbook does not approve a permanent "flash attention off" posture for the
Qwen ROCm container lane.

## Canonical Hemma Discipline

Before any Qwen fine-tune work on Hemma:

```bash
pdm run run-hemma -- rocminfo
pdm run run-hemma -- rocm-smi
pdm run run-local-pdm hemma-verify-gpu-runtime
```

Confirm the repo root and GPU cache roots through the existing runbook:

- remote repo root:
  - `/home/paunchygent/apps/sir-convert-a-lot`
- canonical HF cache:
  - `/srv/scratch/sir-convert-a-lot/cache/huggingface`
- approved home-visible compatibility mount when needed:
  - `/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface`

Always begin long training work from a clean GPU baseline:

```bash
pdm run run-hemma -- rocm-smi --showmeminfo vram --showuse --showpids
```

Pass condition:

- no unrelated KFD PIDs
- only the expected runtime after launch

## Dataset Policy

Planned Swedish sources for Epic 08:

- `KBLab/rixvox`
- `google/fleurs` Swedish
- `KTH/waxholm`

Use them differently:

- `rixvox`:
  - main hours source
  - requires transcript-quality and speaker-quality filtering
- `fleurs`:
  - short clean utterances
  - strong dev/eval source
- `waxholm`:
  - smoke data
  - held-out checks

Do not start by mixing raw multi-thousand-hour `rixvox` data without a curation
policy.

Canonical Task 102 corpus policy:

- `docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md`
- filtered `rixvox` train is the only main training backbone
- `fleurs` validation/test plus labeled `waxholm` stay reserved for control and
  evaluation
- bounded Hemma pilot target:
  - `24` to `36` filtered hours from `24` to `40` speakers
- Colab scale-up target:
  - `100` to `300` filtered hours from `80` to `160` speakers

## Dependency Baseline

Separate the runtime dependencies by lane. Do not treat host-python state as
the contract.

Task 100 training image baseline:

- `qwen_tts`
- ROCm-compatible `torch`
- `accelerate`
- `transformers`
- `safetensors`
- `huggingface_hub`
- `librosa`
- `soundfile`
- `sentencepiece`
- `tensorboard`

Canonical Task 100 runtime assets:

- `containers/qwen-finetune-hemma/Dockerfile`
- `containers/qwen-finetune-hemma/requirements.txt`
- `scripts/sir_convert_a_lot/devops/run_task100_hemma_qwen_finetune_smoke.py`

Wrapper-driven Hemma smoke command for the image surface:

```bash
pdm run run-hemma -- pdm run task-100-smoke
```

Expected deterministic evidence root:

- `build/verification/task-100-qwen-finetune-smoke/`
  - `report.json`
  - `report.md`
  - `failure.txt` when the smoke run fails

Task 103 preprocessing/eval baseline:

- `datasets`
- Swedish ASR runtime/tooling for transcript-mismatch filtering
- `jiwer`
- any committed audio normalization utilities required by the pipeline

Policy:

- the Task 100 image must contain the training baseline itself
- the Task 103 surface must document its own preprocessing/eval stack
- do not rely on mutable host installs on Hemma as the long-term source of
  truth

Canonical Task 103 preprocessing contract:

- `docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md`
- deterministic artifact root:
  - `build/reference/qwen3-tts-swedish-corpus/`
- pinned ASR mismatch backend:
  - `KBLab/kb-whisper-large`
  - `revision="strict"`
- public source assets may begin at `16 kHz`, but all emitted training-side
  audio artifacts and `ref_audio` clips must be `24 kHz`

## Execution Order

1. Complete Task 99 so the Qwen Hemma benchmark reflects the current ROCm flash
   attention policy.
1. Complete Task 105 so the first experiment is anchored to one tracked
   research map, one research-team brief, and one repomix package rather than
   ad hoc notebook hunting.
1. Complete Task 100 and create the dedicated training runtime.
   - include the Task 100 training-image dependency baseline
   - ensure `sft_12hz.py` exports cleanly for both local model directories and
     Hub ids
1. Run the canonical live Hemma Task 100 smoke command:
   - `pdm run run-hemma -- pdm run task-100-smoke`
   - if the smoke run fails, treat it as the last blocker before corpus and
     preprocessing work
   - if the smoke run succeeds, move directly into `T102` and `T103`
1. Complete Task 102 and define the bounded Swedish pilot subset.
1. Complete Task 103 and produce deterministic manifests and preprocessed
   artifacts.
   - include the Task 103 preprocessing/eval dependency baseline
1. Run Task 101 as the first bounded Hemma pilot.
1. Run Task 104 as the Colab H100 scale-up and comparison lane.

## Hemma Versus Colab

Use Hemma for:

- runtime bring-up
- cache and wrapper discipline
- preprocessing validation
- bounded full-finetune pilot work
- memory truth and optimizer-step proof

Use Colab H100 for:

- larger Swedish runs
- faster iteration on longer curated subsets
- checkpoint-heavy experiments that would be slower or more operationally
  expensive on Hemma

## Time Estimates To Carry Forward

These are planning estimates, not acceptance guarantees:

- bounded Swedish pilot subset:
  - Hemma: roughly `1-2` days end to end
  - Colab H100: roughly `0.5-1` day
- larger curated Swedish run:
  - Hemma: multiple days
  - Colab H100: roughly `1-4` days depending on subset size and session churn

The corpus definition in Task 102 must tighten these estimates before execution
tasks can close.

## Evidence Expectations

Every real training or scaling lane must emit:

- exact command surface used
- repo `HEAD`
- runtime/image identity
- dataset slice identity
- cache roots used
- clean-baseline GPU snapshot
- peak VRAM and GPU busy evidence
- checkpoint/output paths
- report Markdown plus machine-readable JSON

Suggested evidence roots:

- `build/verification/task-101-qwen3-tts-swedish-hemma-pilot/`
- `build/verification/task-104-qwen3-tts-swedish-colab-h100/`

## What Not To Do

- Do not run raw host training processes outside the documented container path.
- Do not treat single-speaker custom-voice success as equivalent to general
  Swedish language support.
- Do not redownload model assets into throwaway container-local paths.
- Do not change the public v2 API to expose Qwen-native training or serving
  taxonomy.
- Do not merge this work back into Epic 07 planning as if it were just another
  benchmark lane.
