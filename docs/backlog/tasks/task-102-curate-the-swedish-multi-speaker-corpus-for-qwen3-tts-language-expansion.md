---
id: task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion
title: Curate the Swedish multi-speaker corpus for Qwen3-TTS language expansion
type: task
status: proposed
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
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

- [ ] Corpus inventory with hours, speakers, and transcript caveats.
- [ ] Initial pilot subset definition.
- [ ] Scale-up subset definition.
- [ ] Explicit held-out evaluation split.

## Acceptance Criteria

- [ ] `rixvox` is treated as the dominant hours source and is filtered rather
  than used raw.
- [ ] `fleurs` and `waxholm` are given explicit roles in dev/eval rather than
  being hand-waved into the training pool.
- [ ] The task names the first bounded pilot-hours target and the later scaled
  target.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
