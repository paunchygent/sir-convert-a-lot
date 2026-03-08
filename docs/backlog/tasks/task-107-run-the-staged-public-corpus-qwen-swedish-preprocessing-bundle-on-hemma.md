---
id: 'task-107-run-the-staged-public-corpus-qwen-swedish-preprocessing-bundle-on-hemma'
title: 'Run the staged public-corpus Qwen Swedish preprocessing bundle on Hemma'
type: 'task'
status: 'active'
priority: 'high'
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-106-add-script-free-hugging-face-corpus-adapters-to-the-qwen-swedish-preprocessing-pipeline.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - preprocessing
  - hemma
  - swedish
  - corpora
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the committed Task 103 preprocessing pipeline against the real staged
Hemma public-corpus assets so the repo produces one deterministic
inventory/curated/raw/prepared bundle from `fleurs`, labeled `waxholm`, and
staged `rixvox` metadata before the first bounded Hemma fine-tune.

## PR Scope

- Extend the committed `task-103-preprocess` runner with one explicit
  staged-public-corpus mode rooted at Hemma's DATA-backed raw-corpus path.
- Keep the existing deterministic artifact and report contract under
  `build/reference/qwen3-tts-swedish-corpus/`.
- Load staged source rows from:
  - `google/fleurs` `sv_se` `dev/test`
  - labeled `KTH/waxholm`
  - `KBLab/rixvox` `dev/test` metadata parquet
- Preserve local repo-fixture smoke mode for fast regression checks while
  adding a canonical Hemma command for the staged public-corpus run.
- Record the first live Hemma preprocessing evidence and resulting limitations,
  especially the current `rixvox` metadata-only boundary.

## Deliverables

- [ ] One committed staged-public-corpus Task 103 runner surface.
- [ ] One canonical PDM command for the Hemma public-corpus preprocessing run.
- [ ] One live Hemma preprocessing evidence bundle under
      `build/reference/qwen3-tts-swedish-corpus/`.
- [ ] One docs update that records what is now real, and what remains blocked
      for `rixvox` before `T101`.

## Acceptance Criteria

- [ ] `task-103-preprocess` supports an explicit staged-public-corpus mode
      without breaking repo-fixture smoke mode.
- [ ] The staged-public-corpus mode reads assets from Hemma's DATA-backed raw
      corpus root rather than downloading anything locally.
- [ ] The live Hemma run emits deterministic inventory, curated, raw, and
      prepared artifacts under `build/reference/qwen3-tts-swedish-corpus/`.
- [ ] `fleurs` and labeled `waxholm` are exercised end to end through audio
      normalization, ASR scoring, and Qwen manifest emission.
- [ ] Staged `rixvox` metadata is included in the deterministic bundle without
      pretending that audio materialization already exists.
- [ ] The task records the current blocker for `rixvox` training-family
      manifests: staged audio materialization and train-family mapping.

## Current Plan

1. Add one staged-public-corpus source-loading mode to the committed Task 103
   runner.
1. Validate the new mode locally with adapter-shaped tests.
1. Run the first real Hemma public-corpus preprocessing bundle against the
   staged assets.
1. Record the live evidence and the remaining `rixvox` gap before `T101`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
