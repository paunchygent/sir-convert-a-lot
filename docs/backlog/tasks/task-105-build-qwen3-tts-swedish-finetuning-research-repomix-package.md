---
id: task-105-build-qwen3-tts-swedish-finetuning-research-repomix-package
title: Build the Qwen3-TTS Swedish finetuning research repomix package
type: task
status: completed
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-research-map-2026-03-08.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - swedish
  - research
  - repomix
  - finetuning
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Package the repo's current Qwen Swedish fine-tuning context into one
research-ready bundle so an external research team can efficiently find
upstream solutions, notebook patterns, model-card evidence, and multi-speaker
language-expansion guidance that fits Sir Convert-a-Lot's real Hemma and Colab
lane.

## PR Scope

- Publish one repo-tracked research map that explains:
  - our real setup,
  - current proven facts,
  - current knowledge gaps,
  - and the exact research questions that still matter.
- Publish one repomix research brief tailored to:
  - Hemma,
  - ROCm containers,
  - `Qwen/Qwen3-TTS-12Hz-1.7B-Base`,
  - full fine-tuning,
  - Swedish multi-speaker language expansion.
- Generate one repomix XML package containing the canonical docs, skills,
  runtime references, and backlog surfaces needed for the research pass.

## Deliverables

- [x] Reference research map under `docs/reference/`.
- [x] Research-team prompt under `.agents/repomix_packages/`.
- [x] Generated repomix XML package under `.agents/repomix_packages/`.
- [x] Epic 08 / Story 24 / runbook cross-links updated to point at the new
  package.

## Acceptance Criteria

- [x] The research map distinguishes between:
  - proven repo facts,
  - open decisions,
  - and evidence the research team still needs to fetch.
- [x] The brief asks for targeted evidence from:
  - open Colab notebooks,
  - GitHub repos,
  - Hugging Face model cards,
  - paper-as-code repos,
  - research papers.
- [x] The brief explicitly asks for:
  - a link collection,
  - distilled best practices,
  - and recommendations tailored to this repo's pipeline rather than generic
    TTS advice.
- [x] The repomix package includes the canonical Epic 08 docs, Qwen runbook,
  relevant skills, and the current Qwen Hemma runtime references.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
