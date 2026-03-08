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
  - source audio,
  - normalized transcript,
  - reference audio policy,
  - generated audio codes,
  - train/dev/eval manifests.
- Preserve deterministic artifact/output roots for later reruns.

## Deliverables

- [ ] One committed preprocessing pipeline surface.
- [ ] One documented manifest schema used by Hemma and Colab runs.
- [ ] Runbook guidance for preprocessing reruns and artifact locations.

## Acceptance Criteria

- [ ] The pipeline is compatible with the official Qwen tokenizer/code
  preparation flow.
- [ ] The pipeline produces deterministic manifests for train/dev/eval splits.
- [ ] The pipeline can be reused by both the Hemma pilot and the Colab H100
  scaling lane.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
