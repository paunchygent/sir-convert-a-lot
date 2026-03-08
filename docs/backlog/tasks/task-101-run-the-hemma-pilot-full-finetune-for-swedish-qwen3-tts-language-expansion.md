---
id: task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion
title: Run the Hemma pilot full-finetune for Swedish Qwen3-TTS language expansion
type: task
status: proposed
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - hemma
  - pilot
  - swedish
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the first bounded Hemma pilot full-finetune for Swedish language expansion
on `Qwen/Qwen3-TTS-12Hz-1.7B-Base` and capture deterministic runtime and memory
evidence.

## PR Scope

- Use the committed Hemma runtime from Task 100 plus the first bounded Swedish
  training subset from Tasks 102 and 103.
- Capture:
  - clean idle GPU baseline,
  - startup/runtime metadata,
  - successful optimizer-step evidence,
  - peak VRAM/GPU usage,
  - checkpoint/output locations,
  - failure notes if the run does not complete.
- Keep the lane focused on pilot proof, not maximal dataset hours.

## Deliverables

- [ ] Hemma pilot evidence under `build/verification/`.
- [ ] Machine-readable report for memory/runtime truth.
- [ ] Linked task/runbook updates with the exact command used.

## Acceptance Criteria

- [ ] The pilot uses the `1.7B` base model, not the `0.6B` lane.
- [ ] The run reaches a real Swedish full-finetune optimizer step with `AdamW`.
- [ ] The evidence records actual VRAM usage and headroom on the R9700.
- [ ] The task explicitly states whether Hemma is good enough for the bounded
  pilot and what should move to Colab H100 for scale.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
