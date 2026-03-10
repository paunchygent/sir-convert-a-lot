---
id: 'task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing'
title: 'Add portable-slice localization stage for Colab Qwen preprocessing'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-10'
last_updated: '2026-03-10'
related:
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/backlog/tasks/task-122-run-the-first-live-colab-gpu-portable-slice-qwen-row-processing-proof.md
  - docs/backlog/tasks/task-123-add-resumable-row-processing-for-qwen-preprocessing-runs.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - preprocessing
  - notebook
  - localization
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add a repo-owned portable-slice localization stage for Colab Qwen
row-processing so portable slices can be converted from archive-backed staged
raw assets into plain local audio files plus a persisted localized
selected-source manifest, then rerun the same Colab slice with a more
aggressive `8:2` worker mix without paying the old archive-resolution startup
tax on every attempt.

## PR Scope

- Keep Hemma as the only row-selection authority.
- Extend the portable Colab slice CLI with one localization surface that:
  - reads one portable selected-source bundle,
  - resolves the required local archive members from staged raw files,
  - extracts them into a deterministic local audio tree,
  - writes one localized selected-source JSONL with plain-file locators.
- Keep the notebook thin by invoking that repo-owned localization surface
  before row-processing.
- Switch the Colab follow-on probe to:
  - `row_worker_count=8`
  - `gpu_asr_worker_count=2`
- Preserve Task 103 artifact compatibility and row-processing resume semantics.

## Deliverables

- [x] One repo-owned portable-slice localization command in the existing Task
      121 CLI surface.
- [x] One persisted localized selected-source manifest and localized-audio tree
      rooted under the portable slice directory.
- [x] One Colab notebook flow that runs:
  - required-file staging,
  - slice localization,
  - canonical Task 103 row-processing against the localized manifest.
- [x] One docs update that records why the localization stage exists and why
      the Colab worker mix moved from `4:1` to `8:2`.

## Acceptance Criteria

- [x] Portable selected-source rows can be localized into plain local files
      without notebook-only extraction logic.
- [x] The localization step persists one localized selected-source manifest
      that Task 103 can consume directly.
- [x] Rerunning the Colab row-processing cell reuses the localized manifest and
      localized audio files instead of repeating archive-member resolution.
- [x] The notebook remains an orchestrator around repo-owned commands only.
- [x] The Colab follow-on probe is configured for:
  - `row_worker_count=8`
  - `gpu_asr_worker_count=2`
- [x] Task 103 row-processing resume semantics remain compatible with the
      localized Colab lane.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
