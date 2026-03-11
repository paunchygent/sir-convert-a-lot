---
type: runbook
id: RUN-qwen3-swedish-finetuning-on-hemma-and-colab
title: Qwen3-TTS Swedish Finetuning Runbook for Hemma and Colab
status: active
created: 2026-03-08
updated: 2026-03-11
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
  - docs/backlog/tasks/task-114-hard-isolate-qwen-row-processing-and-finalization-on-hemma.md
  - docs/backlog/tasks/task-111-add-asr-backed-transcript-relabeling-with-provenance-for-qwen-corpus-candidates.md
  - docs/backlog/tasks/task-115-add-fault-tolerant-resumable-qwen-training-checkpoints-on-hemma.md
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/backlog/tasks/task-122-run-the-first-live-colab-gpu-portable-slice-qwen-row-processing-proof.md
  - docs/backlog/tasks/task-123-add-resumable-row-processing-for-qwen-preprocessing-runs.md
  - docs/backlog/tasks/task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing.md
  - docs/backlog/tasks/task-129-prepare-large-portable-colab-slice-for-multi-session-qwen-row-processing.md
  - docs/backlog/tasks/task-131-add-backward-compatible-resume-index-for-drive-backed-qwen-row-processing.md
  - docs/backlog/tasks/task-134-deduplicate-live-colab-remainder-and-enforce-unique-slice-allocation-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-135-plan-canonical-dedupe-of-qwen-preprocessing-storage-backups.md
  - docs/backlog/tasks/task-136-define-immutable-qwen-shard-registry-and-enforced-unique-work-allocation.md
  - docs/backlog/tasks/task-137-implement-canonical-qwen-processed-root-dedupe-and-immutable-shard-allocation.md
  - docs/backlog/tasks/task-138-canonicalize-qwen-pilot-ownership-and-salvage-the-remaining-colab-slice.md
  - docs/backlog/tasks/task-139-synchronize-qwen-shard-governance-across-story-24-epic-08-and-runbook.md
  - docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md
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
- containerized Hemma runtime as the default training and scale lane
- Colab H100 only as an optional fallback or comparison lane when Hemma hits
  real runtime or wall-time limits

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
- Once the pilot canonical processed root is frozen, future preprocessing
  allocation must exclude both its owned rows and its conflict-row manifest.
- The first bounded Task 101 fine-tune must consume a deterministic pilot
  bundle projected from the frozen pilot root, not the generic promoted Task
  103 corpus view.

## Frozen Pilot Dataset Rule

The current canonical pilot-owned preprocessing source is:

- `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`

The next bounded Task 101 launch must use that frozen ownership source through
one deterministic pilot training bundle that contains:

- `manifests/swedish_pilot_train.prepared.jsonl`
- `manifests/swedish_checkpoint_dev.prepared.jsonl`
- stable per-speaker `refs/`
- machine-readable bundle metadata that records:
  - the frozen source root
  - retained row counts
  - manifest families present

Operational rule:

- do not launch Task 101 against the generic promoted preprocessing root
  `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus`
- do not launch Task 101 against ad hoc manually selected row subsets
- materialize the deterministic pilot bundle first, then launch the detached
  Hemma runner from that bundle

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
  detached Task 114 isolated-stage orchestrator
- live Hemma evidence exists under:
  - `build/verification/task-109-qwen-containerized-preprocessing/`

Current `T110` hardening requirement:

- detached and public-corpus preprocessing runs must not execute directly
  inside the canonical shared corpus path
- every live preprocessing run must write to an immutable run root
- the canonical shared corpus path is promotion-only
- failed runs remain inspectable in their original run roots

Completed `T114` hardening shape:

- on Hemma, the canonical GPU-backed preprocessing path is no longer one
  `stage=all` run
- row-processing must complete in one detached fresh container/process
- finalization must then start in a separate detached fresh container/process
- reports and promotion remain separately invokable follow-on stages
- this isolation is mandatory because row-processing is low-load concurrent
  Whisper work, while finalization is high-risk Qwen tokenizer/model
  inference that can wedge the host if it inherits the earlier GPU runtime
- `status.json` now persists row progress plus finalization family/chunk
  heartbeat detail for recovery and inspection

Latest bounded detached `T108` proof on Hemma (`2026-03-09`) confirmed:

- immutable scratch-backed run roots are working as intended
- detached execution is no longer the active failure mode
- the preserved `4`-worker run root shows `swedish_smoke_train` and
  `swedish_pilot_train` completed before the host hard-wedged during
  `swedish_scaleup_train` finalization
- the next runtime fix is therefore strict stage/process isolation, not
  another detached-execution or output-preservation redesign

Recovered `T108` run result after `T114` hard isolation (`2026-03-09`):

- preserved run root:
  - `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task108-4workers-pipeline-20260309T064950Z`
- resumed without rerunning row-processing
- finalized successfully in three fresh detached stages:
  - `swedish_scaleup_train`
  - `swedish_checkpoint_dev,swedish_final_test,swedish_waxholm_control`
  - `reports`
- final report counts:
  - `swedish_smoke_train=52`
  - `swedish_pilot_train=52`
  - `swedish_scaleup_train=58`
  - `swedish_checkpoint_dev=8`
  - `swedish_final_test=8`
  - `swedish_waxholm_control=8`
- canonical promoted corpus view now points at that recovered run root:
  - `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus`

## Training Lane Direction

Current documented direction after the bounded `T101` pilot:

- Hemma is the default training lane for bounded pilot work and the planned
  first scale lane for longer Swedish runs.
- Colab H100 is not the default next step anymore.
- Colab remains an optional fallback or comparison lane only if Hemma shows a
  real limit on:
  - runtime stability,
  - fault-tolerant resume robustness,
  - or unacceptable wall-clock time for the chosen dataset slice.

The bounded detached `T101` pilot already proved:

- real optimizer-step training on Hemma,
- `flash_attention_2` working on the ROCm container path,
- peak reserved VRAM around `20.89 GB` on the `32.06 GB` card,
- successful checkpoint-final export under detached orchestration.

So the next long-run posture is Hemma-first, not H100-first.

## Optional Colab Preprocessing Lane

Colab may assist with row-processing only when it consumes a Hemma-issued
portable slice bundle.

Rules:

- Colab must not independently select rows.
- Colab must not invent a notebook-only preprocessing implementation.
- Colab must reuse the Task 103 runner through the `selected-source-records`
  source mode.
- When the execution lane is Hemma-backed, repo edits, commits, and pushes
  should happen on the Hemma repo clone, then be pulled locally as needed.

When portable Colab throughput needs improvement, the next allowed optimization
is a repo-owned portable-slice localization stage:

- stage only the required raw files first
- localize the selected slice into plain local audio files plus a persisted
  localized selected-source manifest
- then run Task 103 row-processing against that localized manifest

Do not move archive extraction or locator resolution into notebook-only code.
Keep those steps in repo-owned command surfaces.
- Interrupted row-processing runs must eventually resume from the preserved run
  root and existing spool rows instead of restarting from zero; `T123` closes
  that remaining durability gap.
- The first portable remote lane is intentionally limited to `rixvox train`
  row-processing; finalization, reports, promotion, and held-out corpora remain
  on Hemma.

After the `task116`/`task129` overlap incident, future incremental allocation
has a stricter canonical path:

- dedupe completed run roots into one canonical processed root
- build one immutable shard registry from the remaining universe
- issue worker processing units only from shard ids

Canonical commands:

- `python -m scripts.sir_convert_a_lot.devops.task103_qwen_canonical_processed_root build`
- `task-121-colab-slice-bundle build-shard-registry`
- `task-121-colab-slice-bundle issue-processing-unit-from-shards`

Shard rules:

- use roughly `5000` rows per shard by default
- never recreate a shard under a different id
- never issue work outside the shard ledger

`plan-remaining-unique` remains available only for incident recovery and
salvage of already-issued manifests.

If an in-flight Colab manifest must be salvaged after overlap is discovered,
use the repo-owned dedupe surface:

- `task-121-colab-slice-bundle dedupe-selected-source-records`

Point it at the current selected-source manifest and subtract every known
completed run root first. The notebook should then resume against the emitted
deduplicated manifest instead of encoding overlap logic in notebook cells.

First live proof shape:

- create one fresh Hemma `source-selection` universe dedicated to Colab proof
- keep it bounded to roughly `512` `rixvox train` rows
- partition with `slice_count=2`
- assign Colab `slice_index=1`
- run notebook-backed row-processing with:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=1`

This proof must stay independent of the live Hemma `10k` campaign; do not
reuse or merge the current Hemma `source-selection` universe for the first
Colab validation.

## Current Corpus Reality

The current promoted Task 103 corpus view is operationally valid but still a
bounded proof slice rather than the intended bounded Hemma pilot corpus.

Current prepared manifest counts on Hemma:

- `swedish_smoke_train=52`
- `swedish_pilot_train=52`
- `swedish_scaleup_train=58`
- `swedish_checkpoint_dev=8`
- `swedish_final_test=8`
- `swedish_waxholm_control=8`

Current composition:

- train families are still `rixvox`-only
- held-out quantitative families are still dominated by `fleurs`
- the current train-side prepared rows are still effectively one-speaker

Interpretation:

- the preprocessing/training/runtime stack is now proven
- the current corpus is still too narrow to be treated as the real bounded
  multi-speaker Hemma pilot target
- the next operational move is corpus expansion first, not a larger training
  run on the same narrow prepared slice

## Next Corpus-Expansion Posture

The next preprocessing effort should be aimed directly at the bounded Hemma
pilot corpus target from `T102`, not at another tiny proof slice.

Chosen immediate direction:

- expand staged `rixvox` train breadth first
- launch detached `row-processing` only
- use:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=2`
- use `2` hours as a health gate only
- if healthy, let the same detached run continue into an `8` to `10` hour
  window
- do not auto-enter finalization after row-processing

Initial bounded staging plan:

- keep staged `train_0`
- add `train_1` through `train_23`

Reason:

- the next corpus-expansion objective is to grow a real high-trust
  multi-speaker `swedish_pilot_train`
- staging more train breadth is more valuable right now than repeating
  training on the current narrow proof slice

## Duration Policy Clarification

The repo's bounded Hemma pilot `20s` clip target is currently a conservative
repo heuristic, not a strongly evidenced upstream Qwen hard requirement.

What is true:

- the public Qwen model card and finetuning docs do not currently establish a
  clear `<20s` base-model training-clip policy
- the original repo target existed to keep the first Hemma pilot conservative
  on runtime/sequence cost and to avoid domination by long parliamentary clips

Current live evidence:

- the detached `T116` row-processing run is currently averaging admitted clip
  durations around `23.19s`
- that is not treated as a failure signal by itself

Operational rule:

- keep the preprocessing run alive when runtime is healthy
- review duration distribution before finalizing the next real
  `swedish_pilot_train`
- prefer median/tail review plus speaker-balance checks over a blind hard
  cutoff at `20s`

## Fault-Tolerant Resume Contract

Before longer unattended Hemma training windows, the training lane must expose
the durable-resume path delivered through `T115`.

Required contract:

- checkpoints are written at a bounded step cadence during training, not only
  at epoch/final boundaries
- each durable checkpoint persists:
  - model weights,
  - optimizer state,
  - scheduler state if used,
  - `accelerate` trainer/runtime state,
  - latest durable step and epoch metadata
- each Task 101 run root records a machine-readable latest-checkpoint pointer
- detached recovery supports:
  - fresh launch,
  - resume latest from the run root,
  - resume from an explicit checkpoint path
- longer unattended runs are not considered operationally ready until one live
  Hemma proof demonstrates interruption plus successful resume in a fresh
  detached launch

Current implementation status:

- the training lane now has committed step-based trainer-state checkpoints
- the Task 101 run root now records `latest_checkpoint.json`
- the detached Task 101 surface now supports:
  - `resume latest`
  - `resume --checkpoint-path <path>`
- the live Hemma interruption-and-resume proof is now complete:
  - proof bundle:
    `build/verification/task-115-qwen-training-resume-proof/task115-20260309t155615z/`
  - initial run interrupted cleanly from durable checkpoint
    `state-step-00000002`
  - fresh detached resume completed successfully through
    `state-step-00000024`

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

Preprocessing execution tiers:

- live preprocessing runs execute under SSD scratch-backed run roots
- canonical shared corpus outputs are promoted views only
- raw corpora remain on HDD storage

Preferred live run root:

- `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/<run_id>/`

Canonical promoted corpus view:

- `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus/`

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
  - `--runs-root`
  - `--run-id`
  - `--run-root`
  - `--promote-on-success`
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
     detached Task 114 orchestrator, which launches fresh Task 109-backed
     stage containers under one immutable Task 103 run root
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
   - current preprocessing already persists Whisper transcript evidence in
     durable spool rows and curated rows
   - if we later test whether low BLEU rows improve when source text is
     replaced by Whisper text, the main missing work is the approval/promotion
     path into training manifests, not rerunning Whisper for completed rows
1. Run Task 101 as the first bounded Hemma pilot.
   - first materialize the deterministic pilot bundle:
     `pdm run run-hemma -- pdm run task-101-pilot-bundle build`
   - canonical command:
     `pdm run run-hemma -- pdm run task-101-pilot launch`
   - canonical input contract before launch:
     - deterministic pilot bundle projected from the frozen pilot root
     - train family: `swedish_pilot_train`
     - eval family: `swedish_checkpoint_dev`
   - runtime truth:
     - detached launch, status, and report artifacts record both the train and
       held-out eval manifest paths
     - upstream `sft_12hz.py` remains train-only, so held-out evaluation is
       reserved for post-training assessment rather than performed inside the
       training loop
   - inspect the detached pilot with:
     `pdm run run-hemma -- pdm run task-101-pilot status`
   - keep the pilot bounded and evidence-first:
     - default train family: `swedish_pilot_train`
     - default batch size: `1`
     - default max steps: `8`
1. Keep Task 104 as an optional Colab H100 fallback/comparison lane only.
   - use it only if Hemma proves insufficient on stability, checkpoint
     recovery, or unacceptable wall time at larger corpus scale
1. Use the completed Task 115 resume surface for longer unattended Hemma runs.
   - durable step-based checkpoints
   - optimizer/trainer-state persistence
   - detached `resume latest` / `resume --checkpoint-path`

## Transcript Remediation Note

For future BLEU- or transcript-quality remediation experiments:

- use persisted row-processing artifacts first
- canonical retrieval surfaces are:
  - `spool/rows/**/*.json`
  - `curated/*.jsonl`
- those artifacts already preserve:
  - `text_normalized`
  - `asr_transcript`
  - `asr_wer`
  - `asr_model`
  - `asr_revision`

Current limitation:

- final `manifests/*.raw.jsonl` and `manifests/*.prepared.jsonl` do not carry
  `asr_transcript`
- promoting approved ASR text into the training path remains explicit future
  work owned by `T111`
1. Execute Task 116 before the next real long Hemma training window.
   - stage broader `rixvox` train coverage first:
     - keep `train_0`
     - add `train_1` through `train_23`
   - then run detached `row-processing` only with:
     - `row_worker_count=4`
     - `gpu_asr_worker_count=2`
   - if Hemma does not already expose historical host resource time-series
     monitoring, start the committed detached resource sampler in parallel:
     - `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task116_hemma_resource_monitor launch`
     - later inspect with:
       - `... status`
       - `... summary`
   - monitor every `10` minutes
   - treat `2` hours as the first health gate only
   - if healthy, continue the same run into `8` to `10` hours
   - finalize only after the enlarged spool/train yield has been inspected
1. Task 119 is now implemented and live-validated on Hemma; use it as the
   foundation for any renewed aggressive row-processing probe.
   - detached launch `task114-source-selection-20260309t221342z` completed
     cleanly for run root
     `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task119-source-selection-20260309a`
   - status was truthful during preflight instead of remaining `allocated`
   - the bounded `rixvox` train cap was enforced during parquet iteration
   - the run persisted:
     - `source_selection/selected_source_records.jsonl`
     - `source_selection/selection_summary.json`
   - the remaining question is no longer “does preflight stream correctly?”
     but “does a fresh aggressive row-processing launch become productive on
     top of the new `source-selection` stage?”

## Hemma Versus Colab

Use Hemma for:

- runtime bring-up
- cache and wrapper discipline
- preprocessing validation
- bounded full-finetune pilot work
- longer scale-up training when the runtime remains stable
- memory truth and optimizer-step proof

Use Colab H100 only when needed for:

- overflow when Hemma hits hard runtime limits
- comparison work after Hemma evidence exists
- faster iteration only if local wall time becomes operationally unacceptable

## Time Estimates To Carry Forward

These are planning estimates, not acceptance guarantees:

- bounded Swedish pilot subset:
  - Hemma: roughly `1-2` days end to end
- larger curated Swedish run:
  - Hemma: multiple days and now the default planned lane
  - Colab H100: optional fallback only if Hemma evidence becomes unacceptable

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
- median and lowest GPU busy evidence when host monitoring is not otherwise available
- checkpoint/output paths
- report Markdown plus machine-readable JSON

`journald` is not a substitute for historical GPU monitoring by itself. Only
treat system logs as a usable GPU history source when a dedicated sampler
service is already writing periodic GPU samples into the journal.

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
