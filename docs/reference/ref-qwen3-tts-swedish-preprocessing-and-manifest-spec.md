---
type: reference
id: REF-qwen3-tts-swedish-preprocessing-and-manifest-spec
title: Qwen3-TTS Swedish Preprocessing and Manifest Specification
status: active
created: 2026-03-08
updated: 2026-03-08
owners:
  - Olof
links:
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-guide.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
---

## Purpose

Define the canonical preprocessing and manifest contract for the Swedish Qwen
full-finetune lane so Hemma and Colab runs use the same artifact layout,
quality-tier logic, and Qwen-ready manifest shapes.

This reference is the contract target for `T103`.

## Deterministic Artifact Roots

All corpus-preprocessing artifacts should live under:

- `build/reference/qwen3-tts-swedish-corpus/`

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

## Pipeline Stages

The preprocessing flow is fixed to these stages:

1. inventory the approved source datasets and emit deterministic source rows
1. normalize transcript text into a Swedish orthography form suitable for Qwen
1. apply corpus-policy filters from `T102`
1. select exactly one canonical `5` to `10` second reference clip per speaker
1. standardize admitted audio assets from public source format to `24 kHz`
1. run Swedish ASR mismatch scoring with `KBLab/kb-whisper-large`,
   `revision="strict"`
1. assign corpus quality tiers from WER bands and speaker-quality gates
1. materialize the rich curated manifest layer
1. materialize the Qwen raw JSONL layer
1. generate `audio_codes` with the official Qwen tokenizer flow
1. materialize the Qwen prepared JSONL layer used by training

## Audio Contract

Public source assets may arrive at `16 kHz`.

Training-side contract:

- all audio referenced by Qwen manifests must be emitted at `24 kHz`
- all `ref_audio` clips must be emitted at `24 kHz`
- the same `24 kHz` canonical reference clip must be reused for every row of a
  given speaker in the same manifest family

## Quality-Tier Contract

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

## Manifest Layers

### Layer 1: Inventory JSONL

Purpose:

- capture deterministic source-row metadata before filtering

Suggested file pattern:

- `build/reference/qwen3-tts-swedish-corpus/inventory/<dataset>-<split>.jsonl`

Required fields:

- `dataset`
- `source_split`
- `dataset_row_id`
- `source_audio_path`
- `source_sample_rate_hz`
- `duration_seconds`
- `text_raw`
- `text_normalized`
- `speaker_id`
- `speaker_name`
- `speaker_from_id`
- `speaker_total_hours`
- `language`

Optional fields:

- `has_label_files`
- `speaker_audio_meta_ok`
- `boilerplate_group`
- `notes`

### Layer 2: Curated JSONL

Purpose:

- represent the post-filter Swedish corpus with explicit admission decisions

Suggested file pattern:

- `build/reference/qwen3-tts-swedish-corpus/curated/<subset>.jsonl`

Required fields:

- `dataset`
- `source_split`
- `dataset_row_id`
- `speaker_id`
- `speaker_name`
- `speaker_from_id`
- `source_audio_path`
- `audio_24k_path`
- `duration_seconds`
- `text_normalized`
- `reference_audio_24k_path`
- `asr_model`
- `asr_revision`
- `asr_transcript`
- `asr_wer`
- `quality_tier`
- `speaker_quality_gate`
- `dedup_applied`
- `admission_decision`
- `manifest_target`

Recommended values:

- `quality_tier`
  - `high_trust`
  - `medium_trust`
  - `rejected`
- `speaker_quality_gate`
  - `speaker_from_id`
  - `manual_review`
  - `rejected_multi_speaker`

### Layer 3: Qwen Raw JSONL

Purpose:

- feed the official `prepare_data.py` stage

Suggested file pattern:

- `build/reference/qwen3-tts-swedish-corpus/manifests/<subset>.raw.jsonl`

Required Qwen fields:

- `audio`
- `text`
- `ref_audio`

Repo-required metadata fields:

- `speaker_id`
- `dataset`
- `source_split`
- `quality_tier`

Example:

```jsonl
{"audio":"audio_24k/rixvox/train/spk_001/utt_000123.wav","text":"Jag vill åka härifrån.","ref_audio":"refs/spk_001/ref.wav","speaker_id":"spk_001","dataset":"rixvox","source_split":"train","quality_tier":"high_trust"}
```

### Layer 4: Qwen Prepared JSONL

Purpose:

- feed the patched `sft_12hz.py` training path after tokenizer/code generation

Suggested file pattern:

- `build/reference/qwen3-tts-swedish-corpus/manifests/<subset>.prepared.jsonl`

Required fields:

- all Layer 3 fields
- `audio_codes`

## Canonical Manifest Families

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

## Reports

The preprocessing pipeline should emit machine-readable summaries under:

- `build/reference/qwen3-tts-swedish-corpus/reports/`

Required reports:

- `inventory_summary.json`
- `filter_summary.json`
- `reference_selection_summary.json`
- `manifest_summary.json`

## Dependency Baseline

The preprocessing/eval surface is separate from the Task 100 training image.

Minimum documented baseline:

- `datasets`
- `jiwer`
- `transformers`
- `torch`
- `torchaudio` or equivalent committed audio normalization surface
- `librosa`
- `soundfile`
- Swedish ASR runtime for `KBLab/kb-whisper-large`

## Outcome

Task 103 can be considered contract-complete once the repo implements this
specification:

- deterministic artifact roots
- deterministic manifest families
- deterministic quality-tier assignment
- explicit 16 kHz source to 24 kHz training-side standardization
- Qwen raw and prepared JSONL surfaces that both Hemma and Colab can reuse
