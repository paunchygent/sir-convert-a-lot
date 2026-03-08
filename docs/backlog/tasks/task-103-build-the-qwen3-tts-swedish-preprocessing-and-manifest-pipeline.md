---
id: task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline
title: Build the Qwen3-TTS Swedish preprocessing and manifest pipeline
type: task
status: completed
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - preprocessing
  - manifests
  - swedish
  - pipeline
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Build the preprocessing and manifest path that turns the curated Swedish corpus
into Qwen-ready training inputs without relying on ad hoc local scripts.

## PR Scope

- Adapt the official Qwen preprocessing flow to the repo's cache, wrapper, and
  artifact policy.
- Define the normalized intermediate records for:
  - source audio (public corpora may arrive at 16 kHz, but training-side
    artifacts are resampled strictly to 24 kHz),
  - normalized transcript (feeding raw Swedish orthography to the LLM tokenizer with strict punctuation),
  - reference audio policy (**assigning exactly one 5-10 second canonical reference clip per speaker**, reused across all rows for that speaker),
  - generated audio codes,
  - train/dev/eval manifests.
- Patch `dataset.py` to parse multiple speakers, build a `spk_id_map`, and carry a dataset-scoped `speaker_id` through the manifest and batch surfaces for governance, evaluation, and optional future speaker-bank export.
- Preserve deterministic artifact/output roots for later reruns.
- Define the transcript-mismatch filtering path for weakly aligned Swedish data,
  preferably with a reproducible Swedish ASR/WER surface before scale-up.
- Define the **preprocessing/eval dependency baseline** separately from the
  Task 100 training image, including:
  - `datasets`
  - Swedish ASR runtime/tooling
  - `jiwer`
  - any audio normalization utilities required by the committed pipeline

## Deliverables

- [x] One committed preprocessing pipeline surface including the patched `dataset.py`.
- [x] One documented manifest schema used by Hemma and Colab runs, demonstrating the two-layer approach (rich intermediate vs Qwen-ready).
- [x] One documented transcript-mismatch filtering policy for `rixvox`.
- [x] One explicit dependency matrix for preprocessing and eval surfaces.
- [x] Runbook guidance for preprocessing reruns and artifact locations.

## Active Contract

Canonical specification:

- `docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md`

This task now has the following fixed contract:

- deterministic artifact root:
  - `build/reference/qwen3-tts-swedish-corpus/`
- manifest layers:
  - inventory JSONL
  - curated JSONL
  - Qwen raw JSONL
  - Qwen prepared JSONL with `audio_codes`
- pinned ASR mismatch backend:
  - `KBLab/kb-whisper-large`
  - `revision="strict"`
- manifest families:
  - `swedish_smoke_train`
  - `swedish_pilot_train`
  - `swedish_scaleup_train`
  - `swedish_checkpoint_dev`
  - `swedish_final_test`
  - `swedish_waxholm_control`
- training-side audio contract:
  - public source assets may arrive at `16 kHz`
  - all emitted training-side audio and `ref_audio` artifacts must be `24 kHz`

## Acceptance Criteria

- [x] The pipeline is compatible with the official Qwen tokenizer/code
  preparation flow.
- [x] The pipeline produces deterministic manifests for train/dev/eval splits.
- [x] The pipeline enforces the 24kHz and canonical 5-10s ref-audio constraints.
- [x] The preprocessing contract makes it explicit that `speaker_id` is tracked
  metadata while primary conditioning still comes from `ref_audio` /
  `speaker_encoder`.
- [x] The preprocessing/eval dependency set is documented separately from the
  Task 100 training-image dependency set.
- [x] The pipeline can be reused by both the Hemma pilot and the Colab H100
  scaling lane.
- [x] The pipeline pins `KBLab/kb-whisper-large` with `revision="strict"` for
  transcript-mismatch scoring.
- [x] The pipeline materializes `swedish_checkpoint_dev` separately from
  `swedish_final_test`.
- [x] The pipeline enforces 16 kHz source acceptance and 24 kHz emitted
  training-side assets without ambiguity.

## Completed Evidence

The first deterministic Task 103 bundle now exists and is reproducible from the
committed runner surface:

- command:
  - `pdm run task-103-preprocess`
- artifact root:
  - `build/reference/qwen3-tts-swedish-corpus/`
- committed runner/runtime surfaces:
  - `scripts/sir_convert_a_lot/devops/run_task103_qwen_swedish_preprocessing.py`
  - `scripts/sir_convert_a_lot/devops/task103_qwen_preprocessing_core.py`
  - `pyproject.toml`
    - `task-103-preprocess`
    - `qwen-preprocessing` dependency group
- machine-readable evidence:
  - `build/reference/qwen3-tts-swedish-corpus/report.json`
  - `build/reference/qwen3-tts-swedish-corpus/report.md`
  - `build/reference/qwen3-tts-swedish-corpus/reports/inventory_summary.json`
  - `build/reference/qwen3-tts-swedish-corpus/reports/filter_summary.json`
  - `build/reference/qwen3-tts-swedish-corpus/reports/reference_selection_summary.json`
  - `build/reference/qwen3-tts-swedish-corpus/reports/manifest_summary.json`
- current runtime truth from the first deterministic bundle:
  - `inventory_rows=2`
  - `curated_rows=2`
  - `admitted_rows=2`
  - `prepared_rows=2`
  - `swedish_smoke_train=2`
  - all other canonical manifest families are emitted as deterministic empty
    JSONL files until the public corpus adapters land

This closes the first committed preprocessing slice. The next extension of
`T103` is to replace the repo-fixture smoke rows with the real public corpus
adapters for `rixvox`, `fleurs`, and labeled `waxholm`.

That public-corpus extension now exists through `T107`. The current remaining
preprocessing blocker before `T101` is `T108`: real `rixvox` audio
materialization plus train-family mapping.

Runtime correction after the first public-corpus pass:

- the original `T107` live run executed on the Hemma host venv and proved the
  public-corpus bundle shape
- `T109` remediated that drift and moved
  `task-103-preprocess-public-corpus` onto the canonical containerized Qwen
  runtime
- live container-backed evidence now exists under:
  - `build/verification/task-109-qwen-containerized-preprocessing/`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
