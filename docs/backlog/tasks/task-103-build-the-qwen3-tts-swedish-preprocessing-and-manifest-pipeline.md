---
id: task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline
title: Build the Qwen3-TTS Swedish preprocessing and manifest pipeline
type: task
status: proposed
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
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

- [ ] One committed preprocessing pipeline surface including the patched `dataset.py`.
- [ ] One documented manifest schema used by Hemma and Colab runs, demonstrating the two-layer approach (rich intermediate vs Qwen-ready).
- [ ] One documented transcript-mismatch filtering policy for `rixvox`.
- [ ] One explicit dependency matrix for preprocessing and eval surfaces.
- [ ] Runbook guidance for preprocessing reruns and artifact locations.

## Acceptance Criteria

- [ ] The pipeline is compatible with the official Qwen tokenizer/code
  preparation flow.
- [ ] The pipeline produces deterministic manifests for train/dev/eval splits.
- [ ] The pipeline enforces the 24kHz and canonical 5-10s ref-audio constraints.
- [ ] The preprocessing contract makes it explicit that `speaker_id` is tracked
  metadata while primary conditioning still comes from `ref_audio` /
  `speaker_encoder`.
- [ ] The preprocessing/eval dependency set is documented separately from the
  Task 100 training-image dependency set.
- [ ] The pipeline can be reused by both the Hemma pilot and the Colab H100
  scaling lane.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
