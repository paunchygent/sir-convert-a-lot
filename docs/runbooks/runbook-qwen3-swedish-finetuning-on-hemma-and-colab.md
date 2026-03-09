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
  - docs/backlog/tasks/task-106-add-script-free-hugging-face-corpus-adapters-to-the-qwen-swedish-preprocessing-pipeline.md
  - docs/backlog/tasks/task-107-run-the-staged-public-corpus-qwen-swedish-preprocessing-bundle-on-hemma.md
  - docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-109-containerize-qwen-public-corpus-preprocessing-execution-on-hemma.md
  - docs/backlog/tasks/task-110-split-qwen-preprocessing-into-disk-backed-row-processing-and-finalization.md
  - docs/backlog/tasks/task-111-add-asr-backed-transcript-relabeling-with-provenance-for-qwen-corpus-candidates.md
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

## Runtime-Model Correction

The intended processing unit for the Qwen lane is the containerized runtime,
not the Hemma host virtualenv.

Historical drift that was corrected by `T109`:

- `T100` correctly established the dedicated containerized Qwen runtime
- `T103` began as a repo/PDM preprocessing runner for fast manifest proof
- `T107` extended that runner into real public-corpus execution on the Hemma
  host venv

That produced an unplanned split between containerized training truth and
host-executed preprocessing truth.

Current canonical position after `T109`:

- containerized Qwen runtime is canonical for preprocessing and training
- Hemma host is orchestration only
- `pdm run task-103-preprocess-public-corpus` now dispatches to the
  containerized Task 109 runtime
- live Hemma evidence exists under:
  - `build/verification/task-109-qwen-containerized-preprocessing/`

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

Verified Hemma storage tiers:

- fast SSD work tier:
  - `/srv/scratch`
  - Docker root/BuildKit cache
  - HF/model caches
  - active generated preprocessing/training artifacts
- large HDD bulk-data tier:
  - `/srv/storage`
  - raw Swedish corpora
  - colder retained datasets
- OS disk:
  - `/`
  - not a valid long-term target for Docker persistent state or large Qwen
    artifact trees

Always begin long training work from a clean GPU baseline:

```bash
pdm run run-hemma -- rocm-smi --showmeminfo vram --showuse --showpids
```

Pass condition:

- no unrelated KFD PIDs
- only the expected runtime after launch

## Detached Hemma Rule

For the Qwen lane, attached client-driven Hemma execution is probe-only.

- Long-running preprocessing, corpus staging, and fine-tuning runs must start
  detached from the local client session.
- Preferred surfaces:
  - committed detached Hemma runner
  - named detached Docker container with later `inspect`, `logs`, and report
    collection
  - remote supervisor or `tmux` only when the repo does not yet expose a
    committed detached runner

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

## Hugging Face Ingestion Policy

The canonical repo path for public-corpus acquisition is not custom
`datasets.load_dataset(...)` scripts.

Preferred path:

- acquire dataset assets with `huggingface_hub` on Hemma only
- pin every acquisition to a dataset revision or commit
- prefer targeted file acquisition over broad whole-repository downloads for
  large corpora
- parse raw supported repository assets directly

Current expected surfaces:

- `rixvox`
  - metadata parquet plus audio archives/files
- `fleurs` Swedish
  - `sv_se` TSV plus audio tarballs
- `waxholm`
  - repo snapshot plus `.wav` and `.smp.mix`

Allowed but non-canonical:

- Hub auto-converted parquet when available as an optimization layer

Not allowed as the long-term repo contract:

- relying on deprecated dataset scripts as the primary ingestion path
- pinning legacy `datasets<4` and using custom dataset scripts, even as a
  fallback

Storage policy:

- large raw corpus assets belong on Hemma's HDD storage tier
- do not download large public corpus assets onto the local workstation
- do not use the Hemma OS disk as the long-term storage location for Swedish
  corpus acquisition
- canonical Hemma raw-corpus root:
  - `/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus/`
- compatible home-visible bind mount when needed:
  - `/home/paunchygent/.data/sir-convert-a-lot/data/qwen3-tts-swedish-corpus/`

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

Current proven Task 100 runtime truth:

- `build/verification/task-100-qwen-finetune-smoke/report.json`
- image id:
  - `sha256:032e235123018c18a85e0abd7a1882aa35289bb7737af1f031befdf35e34f74b`
- `flash_attn==2.8.3`
- `flash_attn_importable == True`
- `flash_attn_model_load_ok == True`
- `HF_HOME` is the canonical cache env for this lane
- `dtype=` is the canonical model-loading keyword for this lane

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

Canonical repo surface for the preprocessing lane:

- install:
  - `pdm install -G qwen-preprocessing`
- run:
  - `pdm run task-103-preprocess`
- runner:
  - `scripts/sir_convert_a_lot/devops/run_task103_qwen_swedish_preprocessing.py`
- current deterministic artifact root:
  - `build/reference/qwen3-tts-swedish-corpus/`
- first bundle truth:
  - `inventory_rows=2`
  - `curated_rows=2`
  - `admitted_rows=2`
  - `prepared_rows=2`
  - `swedish_smoke_train=2`

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
- Hemma storage rule:
  - large generated Qwen preprocessing artifacts and detached-proof evidence
    must persist on the SSD scratch tier, not under the near-full root-backed
    repo `build/` path
- committed runner surfaces:
  - `pdm run task-103-preprocess`
  - `pdm run task-103-preprocess-public-corpus`
- current Task 110 control surfaces on the committed runner:
  - `--stage`
  - `--finalization-families`
  - `--audio-codes-chunk-size`
  - `--row-worker-count`
  - `--gpu-asr-worker-count`

Canonical Task 106 acquisition surface:

- runner:
  - `scripts/sir_convert_a_lot/devops/run_task106_hemma_qwen_corpus_acquisition.py`
- runtime:
  - `scripts/sir_convert_a_lot/devops/task106_qwen_corpus_acquisition_runtime.py`
- local command surface:
  - `pdm run task-106-acquire`
- canonical Hemma execution:
  - `pdm run run-hemma -- pdm run task-106-acquire`
- current bounded default behavior:
  - `fleurs dev/test`
  - `rixvox dev/test metadata parquet`
  - bounded labeled `waxholm` subset via `--waxholm-max-files`
- acquisition discipline:
  - targeted `hf_hub_download(...)`
  - sequential requests with retry/backoff
  - stage raw assets under
    `/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus/`
- first live bounded Hemma execution on `2026-03-08`:
  - `pdm run run-hemma -- pdm run task-106-acquire --waxholm-max-files 8 --request-pause-seconds 0.5`
  - staged counts:
    - `google/fleurs`: `4`
    - `KTH/waxholm`: `17`
    - `KBLab/rixvox`: `2`
  - report path on Hemma:
    `build/reference/qwen3-tts-swedish-corpus/acquisition/report.json`

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
   - prove the first deterministic bundle under
     `build/reference/qwen3-tts-swedish-corpus/`
1. Extend the completed Task 103 surface from repo-fixture smoke rows to the
   real `rixvox` / `fleurs` / labeled `waxholm` corpus adapters.
   - use `T106` Hemma-only acquisition first
   - do not stage large corpus assets on the local workstation
1. Run `T107` and prove the staged public-corpus preprocessing bundle on
   Hemma.
   - canonical command:
     `pdm run run-hemma -- pdm run task-103-preprocess-public-corpus`
   - current proven bounded result:
     - `inventory_rows=16841`
     - `curated_rows=24`
     - `prepared_rows=23`
1. Resolve `T108` before `T101`.
   - `rixvox` is still metadata-only in the preprocessing lane
   - admitted train families remain blocked on `rixvox` audio materialization
     plus train-family mapping
1. Treat `T109` as complete and use the container-backed preprocessing command
   as the canonical runtime path.
   - `pdm run task-103-preprocess-public-corpus` now dispatches to the
     containerized Task 109 runner
   - live remediation evidence exists under
     `build/verification/task-109-qwen-containerized-preprocessing/`
1. Treat `T110` as the active resilience hardening slice for the next detached
   `T108` proof.
   - row preprocessing and finalization are now split
   - row-level ASR/admission results persist as durable spool rows
   - finalization rebuilds canonical refs from the spool
   - `audio_codes` generation is chunked rather than whole-family all-at-once
   - detached Hemma proof work should tune `row-worker-count`,
     `gpu-asr-worker-count`, and `audio-codes-chunk-size` from live evidence
   - latest aggressive proof result:
     - `row-worker-count=10`
     - `gpu-asr-worker-count=5`
     - `audio-codes-chunk-size=4`
     - failed with `ExitCode=139`
     - kernel log showed a segfault in `libaotriton_v2.so.0.11.1`
   - operational constraint now confirmed on Hemma:
     - root (`/`) is nearly full
     - SSD scratch (`/srv/scratch`) is the safe target for hot output and
       caches
     - HDD storage (`/srv/storage`) is the canonical target for raw corpus
       data
1. Keep `T111` as the provenance-safe transcript-improvement lane.
   - ASR remains a quality gate by default
   - any transcript relabeling must preserve original text plus provenance
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

For long preprocessing runs after `T110`, evidence should also record:

- stage selection used
- row-worker count
- GPU ASR worker count
- `audio_codes` chunk size
- whether the run was row-processing only, finalization only, or full pipeline
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
