---
id: task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion
title: Curate the Swedish multi-speaker corpus for Qwen3-TTS language expansion
type: task
status: completed
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - swedish
  - corpus
  - rixvox
  - fleurs
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the bounded Swedish multi-speaker corpus that the Qwen full-finetune
lane will actually use.

## PR Scope

- Inventory the available Swedish datasets already approved for this lane:
  - `KBLab/rixvox`,
  - `google/fleurs` Swedish,
  - `KTH/waxholm`.
- Define transcript-quality and speaker-quality filters.
- Define the first bounded pilot subset plus the later scale-up subset.
- Define train/dev/eval/held-out speaker splits.

## Deliverables

- [x] Corpus inventory with hours, speakers, and transcript caveats.
- [x] Initial pilot subset definition.
- [x] Scale-up subset definition.
- [x] Explicit held-out evaluation split.

## Acceptance Criteria

- [x] `rixvox` is treated as the dominant hours source and is filtered rather
  than used raw.
- [x] `fleurs` and `waxholm` are given explicit roles in dev/eval rather than
  being hand-waved into the training pool.
- [x] The task names the first bounded pilot-hours target and the later scaled
  target.

## Completed Definition

Canonical output:

- `docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md`

Task 102 now fixes the corpus policy for Epic 08:

- filtered `rixvox` train is the only main training backbone
- `fleurs` validation/test and labeled `waxholm` stay reserved for control and
  evaluation
- checkpoint-dev is fixed to:
  - `rixvox` validation plus `fleurs` validation
- final reporting is fixed to:
  - `rixvox` test plus `fleurs` test
- preprocessing smoke subset:
  - `8` to `12` filtered hours from `12` to `16` speakers
- bounded Hemma pilot subset:
  - `24` to `36` filtered hours from `24` to `40` speakers
- Colab scale-up subset:
  - `100` to `300` filtered hours from `80` to `160` speakers
- held-out quantitative evaluation:
  - `rixvox` validation/test plus `fleurs` validation/test
- auxiliary held-out control:
  - labeled usable `waxholm`
- transcript-mismatch filtering hand-off to `T103`:
  - pinned Swedish ASR backend:
    - `KBLab/kb-whisper-large` with `revision=\"strict\"`
  - ASR-WER `<= 0.15` for high-trust smoke/pilot admission
  - ASR-WER `<= 0.20` for medium-trust scale-up admission
  - `speaker_from_id=True` preferred for smoke/pilot; quarantine the rest until
    manual review
  - apply boilerplate-text dedup before per-speaker cap accounting
  - treat the bounded-Hemma pilot `20s` clip target as soft guidance rather
    than a hard upstream-Qwen rule; revise final pilot selection from live
    duration/runtime evidence

## Hand-Off to T103

`T103` now owns:

- generating deterministic artifact specs under
  `build/reference/qwen3-tts-swedish-corpus/`
- implementing the Swedish ASR/WER mismatch filter
- standardizing public `16 kHz` source assets to `24 kHz` before training
  manifests are emitted
- assigning one canonical `5` to `10` second `ref_audio` clip per speaker
- materializing train/dev/eval manifests from this policy

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
