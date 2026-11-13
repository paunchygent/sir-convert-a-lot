---
type: reference
id: REF-SIRCON-GENERAL-qwen3-tts-swedish-preprocessing-and-manifest-specification
title: Qwen3-TTS Swedish Preprocessing and Manifest Specification
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: general
summary: Qwen3-TTS Swedish Preprocessing and Manifest Specification
retired_ids:
- REF-qwen3-tts-swedish-preprocessing-and-manifest-spec
---

## Overview

## Facts And Semantics

## Decisions And Interpretation

## Historical Source Content

### Purpose

Define the canonical preprocessing and manifest contract for the Swedish Qwen
full-finetune lane so Hemma and Colab runs use the same artifact layout,
quality-tier logic, and Qwen-ready manifest shapes.

This reference is the contract target for `T103` and its planned follow-on
hardening tasks `T110` and `T111`.

Portable remote row-processing is allowed only through a Hemma-issued portable
slice bundle. Colab or other remote notebook runtimes must not select rows
independently and must reuse the same Task 103 row-processing contract.

### Source Acquisition Contract

The canonical source-acquisition path for the Swedish Qwen corpus lane is
script-free and revision-pinned.

Preferred long-term path:

- use `huggingface_hub` to acquire dataset assets by pinned revision
- prefer targeted `hf_hub_download(...)` acquisition over broad whole-repo
  fetches for large datasets
- use narrow directory or file acquisition plans only when structure matters
- parse supported raw repository assets directly

Storage policy:

- large raw corpus assets must be acquired on Hemma only
- large raw corpus assets must live on Hemma's HDD storage tier, not on the
  local workstation and not on the Hemma OS disk
- canonical Hemma raw-corpus root:
  - `/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus/`
- compatible home-visible bind mount when needed:
  - `/home/paunchygent/.data/sir-convert-a-lot/data/qwen3-tts-swedish-corpus/`
- on Hemma, large generated preprocessing artifacts and proof evidence must
  live on the SSD scratch tier, not the root disk
- canonical Hemma generated-build root:
  - `/srv/scratch/sir-convert-a-lot/build/`
- compatible home-visible bind mount when needed:
  - `/home/paunchygent/.data/sir-convert-a-lot/build/`

Dataset-specific expected inputs:

- `KBLab/rixvox`
  - metadata parquet
  - repository audio archives / extracted files
- `google/fleurs` Swedish
  - `sv_se` TSV files
  - corresponding audio tar members
- `KTH/waxholm`
  - repo snapshot
  - `.wav`
  - `.smp.mix`

Allowed optional acceleration:

- Hub auto-converted parquet or viewer-derived assets
  - may be used opportunistically when available
  - must not be the only path required for repo success

Forbidden option:

- legacy `datasets<4` custom-script loading
  - forbidden, including as a fallback
  - too brittle for the long-term repo contract

### Deterministic Artifact Roots

Logical artifact structure should remain under:

- `build/reference/qwen3-tts-swedish-corpus/`

Storage interpretation:

- local workstation / repo-fixture runs may use repo-relative `build/...`
- Hemma public-corpus and detached-proof runs must persist the same logical
  subtree under the SSD-scratch-backed build root:
  - `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus/`

Canonical subtrees:

- `inventory/`
  - dataset-level raw inventory and row metadata
- `curated/`
  - filtered corpus records after speaker/text gates
- `refs/`
  - selected canonical per-speaker reference clips
- `audio_24k/`
  - normalized 24 kHz training-side audio assets
- `manifests/`
  - Qwen-ready JSONL manifests for smoke, pilot, scale-up, checkpoint-dev, and
    final test
- `reports/`
  - policy summaries and counts
- `spool/`
  - planned `T110` subtree for disk-backed row-processing outputs used by
    later finalization
  - expected subtrees:
    - `rows/`
    - `tmp/`
    - `state/`

### Run-Scoped Execution Roots

Detached Hemma and public-corpus preprocessing runs must not execute directly
inside the canonical shared corpus path.

Required live execution posture:

- allocate one immutable run root per preprocessing run under SSD scratch
- write all live run artifacts into that run root
- preserve failed and interrupted run roots for later inspection
- treat `build/reference/qwen3-tts-swedish-corpus/` as a promoted view only

Preferred Hemma run-root layout:

- `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/<run_id>/`

Required run-level files:

- `run.json`
- `status.json`
- `logs/`

Promotion contract:

- only a successful run may update the canonical shared corpus view
- promotion must not mutate the run root in place
- failed runs must never overwrite the canonical shared corpus view

### Canonical Processed Root Contract

Once more than one Task 103 run root exists, the canonical processed truth
must be materialized explicitly rather than inferred from multiple live roots.

Required posture:

- original run roots remain immutable evidence
- one canonical processed root is built from ordered run roots
- row identity is `(dataset, source_split, dataset_row_id)`
- same-row conflicts must be quarantined, not silently merged

Canonical surface:

- `python -m scripts.sir_convert_a_lot.devops.task103_qwen_canonical_processed_root build`

Required canonical-root outputs:

- deduplicated `spool/rows/`
- reachable `audio_24k/`
- rebuilt `completed_row_keys.jsonl`
- `reports/canonical_processed_root_report.json`
- `reports/canonical_processed_root_duplicates.jsonl`
- `reports/canonical_processed_root_conflicts.jsonl`
- `reports/canonical_processed_root_owned_row_keys.jsonl`
- `reports/canonical_processed_root_conflict_row_keys.jsonl`
- `reports/canonical_processed_root_freeze.json`

Freeze rule:

- once a canonical processed root is promoted as the pilot-owned truth, that
  immutable root plus `canonical_processed_root_freeze.json` become the frozen
  pilot dataset surface
- future allocation must treat
  `reports/canonical_processed_root_conflict_row_keys.jsonl` as unavailable
  work, not as “maybe reusable later”

### Pipeline Stages

The full planned preprocessing flow, including `T110` / `T111` hardening, is
fixed to these stages:

1. inventory the approved source datasets and emit deterministic source rows
1. normalize transcript text into a Swedish orthography form suitable for Qwen
1. apply corpus-policy filters from `T102`
1. select exactly one canonical `5` to `10` second reference clip per speaker
1. standardize admitted audio assets from public source format to `24 kHz`
1. run Swedish ASR mismatch scoring with `KBLab/kb-whisper-large`,
   `revision="strict"`
1. assign corpus quality tiers from WER bands and speaker-quality gates
1. persist row-level preprocessing results to a deterministic disk-backed spool
1. materialize the rich curated manifest layer from the spool
1. materialize the Qwen raw JSONL layer from the spool
1. generate `audio_codes` with the official Qwen tokenizer flow in bounded
   chunks
1. materialize the Qwen prepared JSONL layer used by training

### Stage Control Contract

The preprocessing lane should be independently controllable by stage.

Required stage surfaces:

- `run-allocation`
- `inventory`
- `row-processing`
- `curated-projection`
- `finalization`
- `reports`
- `promotion`

Preferred execution behavior:

- each stage can be run independently
- later stages consume deterministic on-disk artifacts from earlier stages
- rerunning later stages must not require recomputing already completed
  row-processing work

### Immutable Shard Allocation Contract

Once a canonical processed root exists, the remaining source-selection universe
must be cut into immutable shards before new worker assignments are issued.

Required posture:

- default shard target is roughly `5000` rows
- shard ids are immutable and must never be recreated under another id
- processing units must be issued from shard ids only
- assignment state must be persisted in one append-only ledger
- assigned or completed shard ids must be rejected for reissuance
- explicit row-key exclusion manifests must be supported for quarantined
  conflict rows

Canonical surfaces:

- `task-121-colab-slice-bundle build-shard-registry`
- `task-121-colab-slice-bundle issue-processing-unit-from-shards`
- `task-121-colab-slice-bundle release-processing-unit`
- `task-121-colab-slice-bundle complete-processing-unit`

Required exclusion posture for future shard issuance:

- exclude the frozen pilot-owned rows through the canonical processed root
- exclude the frozen pilot conflict rows through:
  - `--exclude-row-keys-path <canonical_processed_root_conflict_row_keys.jsonl>`

Hemma hard-isolation rule:

- GPU-backed public-corpus runs on Hemma must not use one long-lived
  `stage=all` process as the canonical path
- `row-processing` and `finalization` must run in separate fresh
  containers/processes
- `reports` and `promotion` should also remain independently invokable
- finalization must start from a cold runtime with no carried-over Whisper
  worker state from row-processing
- live `status.json` must persist row progress plus finalization family/chunk
  heartbeat so recovery does not depend on artifact archaeology

### Parallelism Contract

Parallelism must be explicit and bounded.

Required control knobs:

- row-worker count
- CPU-side audio materialization concurrency
- GPU-side ASR worker count
- finalization-family selection
- `audio_codes` chunk size

Default posture:

- conservative GPU concurrency
- sequential family finalization
- chunked `audio_codes` generation
- detached Hemma execution for long runs
- stage-by-stage orchestration on Hemma rather than one combined GPU-backed
  `all` stage

### Modularization Contract

The preprocessing lane should be split into stage-oriented modules rather than
expanded indefinitely inside one file.

Preferred module boundaries:

- orchestration runner
- source loading and inventory
- row processing
- ASR mismatch scoring
- spool read/write contract
- manifest finalization
- reporting

Module policy:

- schema types should live in dedicated model/contract modules
- stage entrypoints should be independently testable
- no future hardening task should rely on growing one central preprocessing
  file without decomposition

### Spool Contract

`T110` should treat the spool as the durable hand-off between row-processing
and finalization.

Expected spool semantics:

- one durable completed-row record per processed source row
- temp-file plus atomic-rename writes
- no partial row treated as complete
- enough row metadata to rebuild curated/manifests/reports without rerunning
  Whisper for completed rows
- spool rows are durable within one run root and are not shared across runs

Minimum planned spool fields:

- source identity:
  - `dataset`
  - `source_split`
  - `dataset_row_id`
- materialized artifact paths:
  - `audio_24k_path`
  - `reference_audio_24k_path`
- transcript and quality state:
  - `text_normalized`
  - `asr_transcript`
  - `asr_wer`
  - `quality_tier`
  - `speaker_quality_gate`
  - `admission_decision`
- routing state:
  - `manifest_targets`

### Audio Contract

Public source assets may arrive at `16 kHz`.

Training-side contract:

- all audio referenced by Qwen manifests must be emitted at `24 kHz`
- all `ref_audio` clips must be emitted at `24 kHz`
- the same `24 kHz` canonical reference clip must be reused for every row of a
  given speaker in the same manifest family

### Transcript Provenance Contract

This is the planned `T111` extension to the current preprocessing contract.

Source transcript text remains canonical by default.

ASR output is required for mismatch scoring and quality-tier assignment. It is
not automatically allowed to replace the public-source transcript.

Current persisted state already includes the Whisper-side transcript evidence
needed for a later relabeling experiment:

- durable spool rows persist:
  - `asr_model`
  - `asr_revision`
  - `asr_transcript`
  - `asr_wer`
- curated rows also preserve:
  - `asr_model`
  - `asr_revision`
  - `asr_transcript`
  - `asr_wer`

Practical implication:

- a future transcript-remediation evaluation should reuse these persisted ASR
  transcripts from `spool/rows/` or `curated/*.jsonl`
- rerunning Whisper for already completed rows is not required as long as the
  run root or promoted corpus view is retained
- the missing contract is the provenance-safe promotion path into training
  manifests, not additional ASR persistence during row-processing

Important current limitation:

- final Qwen raw/prepared training manifests do **not** retain
  `asr_transcript`
- they currently carry only the training `text` field, which remains sourced
  from canonical normalized public-source transcript text

If the relabeling lane is enabled, the curated/report layers must preserve
both:

- original source transcript text
- ASR-generated transcript text

Any relabeling decision must be explicit and machine-readable.

### Quality-Tier Contract

Pinned Swedish ASR backend:

- model:
  - `KBLab/kb-whisper-large`
- revision:
  - `strict`

Quality tiers:

- `high_trust`
  - WER `<= 0.15`
  - admissible for smoke subset and bounded Hemma pilot
- `medium_trust`
  - WER `> 0.15` and `<= 0.20`
  - admissible for scale-up only
- `rejected`
  - WER `> 0.20`

Speaker-quality rules:

- prefer `speaker_from_id=True` rows for smoke and pilot manifests
- quarantine rows without `speaker_from_id=True` until manual review proves the
  speaker mapping is safe
- reject suspected multi-speaker contamination or diarization failures
- apply boilerplate-text dedup before per-speaker cap accounting

### Manifest Layers

- Inventory JSONL: deterministic source-row metadata before filtering; path
  `build/reference/qwen3-tts-swedish-corpus/inventory/<dataset>-<split>.jsonl`;
  required fields `dataset`, `source_split`, `dataset_row_id`,
  `source_audio_path`, `source_sample_rate_hz`, `duration_seconds`, `text_raw`,
  `text_normalized`, `speaker_id`, `speaker_name`, `speaker_from_id`,
  `speaker_total_hours`, `language`; optional fields `has_label_files`,
  `speaker_audio_meta_ok`, `boilerplate_group`, `notes`.
- Curated JSONL: post-filter Swedish corpus with explicit admission decisions;
  path `build/reference/qwen3-tts-swedish-corpus/curated/<subset>.jsonl`;
  required fields `dataset`, `source_split`, `dataset_row_id`, `speaker_id`,
  `speaker_name`, `speaker_from_id`, `source_audio_path`, `audio_24k_path`,
  `duration_seconds`, `text_normalized`, `reference_audio_24k_path`,
  `asr_model`, `asr_revision`, `asr_transcript`, `asr_wer`, `quality_tier`,
  `speaker_quality_gate`, `dedup_applied`, `admission_decision`,
  `manifest_target`; recommended `quality_tier` values `high_trust`,
  `medium_trust`, `rejected`, and `speaker_quality_gate` values
  `speaker_from_id`, `manual_review`, `rejected_multi_speaker`; planned T111
  fields `text_original`, `transcript_source`, `relabel_decision`, with
  `transcript_source` values `source`, `asr_candidate`, `asr_approved` and
  `relabel_decision` values `not_attempted`, `candidate_only`, `approved`,
  `rejected`.
- Qwen Raw JSONL: input to official `prepare_data.py`; path
  `build/reference/qwen3-tts-swedish-corpus/manifests/<subset>.raw.jsonl`;
  required Qwen fields `audio`, `text`, `ref_audio` plus repo metadata
  `speaker_id`, `dataset`, `source_split`, `quality_tier`.
- Qwen Prepared JSONL: input to patched `sft_12hz.py` after tokenizer/code
  generation; path
  `build/reference/qwen3-tts-swedish-corpus/manifests/<subset>.prepared.jsonl`;
  required fields are all Layer 3 fields plus `audio_codes`.
### Canonical Manifest Families

The preprocessing pipeline should materialize these manifest families:

- `swedish_smoke_train`
- `swedish_pilot_train`
- `swedish_scaleup_train`
- `swedish_checkpoint_dev`
- `swedish_final_test`
- `swedish_waxholm_control`

Family roles:

- `swedish_checkpoint_dev`
  - `rixvox` validation plus `fleurs` validation
- `swedish_final_test`
  - `rixvox` test plus `fleurs` test
- `swedish_waxholm_control`
  - labeled usable `waxholm` only

### Outcome

Task 103 can be considered contract-complete once the repo implements this
specification:

- deterministic artifact roots
- deterministic manifest families
- deterministic quality-tier assignment
- explicit 16 kHz source to 24 kHz training-side standardization
- Qwen raw and prepared JSONL surfaces that both Hemma and Colab can reuse
