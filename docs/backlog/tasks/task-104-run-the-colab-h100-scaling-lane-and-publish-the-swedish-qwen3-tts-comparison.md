---
id: task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison
title: Run the Colab H100 scaling lane and publish the Swedish Qwen3-TTS comparison
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
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - h100
  - comparison
  - swedish
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the scaled Colab H100 Swedish Qwen lane and publish the comparison against
the Hemma pilot.

## PR Scope

- Reuse the same curated Swedish data and manifest policy from Tasks 102 and
  103\.
- Define checkpoint cadence and evidence export for Colab session limits.
- Compare Colab H100 against Hemma on:
  - runtime throughput,
  - checkpoint behavior,
  - operational friction,
  - qualitative Swedish output.

## Deliverables

- [ ] One Colab H100 run report.
- [ ] One Hemma-versus-Colab comparison summary.
- [ ] Updated runbook guidance for when to use Hemma and when to use Colab.

## Acceptance Criteria

- [ ] The task records the exact dataset slice and checkpoint strategy used on
  Colab.
- [ ] The task compares results against the Hemma pilot instead of publishing a
  standalone notebook-only result.
- [ ] The task records whether the Colab lane is materially better for the
  larger Swedish run.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
