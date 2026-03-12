---
id: task-129-prepare-large-portable-colab-slice-for-multi-session-qwen-row-processing
title: Prepare large portable Colab slice for multi-session Qwen row-processing
type: task
status: completed
priority: high
created: '2026-03-10'
last_updated: '2026-03-10'
related:
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/backlog/tasks/task-123-add-resumable-row-processing-for-qwen-preprocessing-runs.md
  - docs/backlog/tasks/task-127-add-progress-logging-for-colab-portable-slice-staging-and-localization.md
  - docs/backlog/tasks/task-128-add-colab-gpu-preflight-guard-before-portable-slice-row-processing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - preprocessing
  - notebook
  - scaling
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Prepare the next large portable Colab slice so one assigned Colab worker can
resume the same disjoint row-processing slice over two to three 10-hour
sessions without reprocessing completed rows.

## PR Scope

- Set the next notebook constants for a large Colab-owned slice.
- Move the Colab run root onto persistent Google Drive storage for cross-session
  resume safety.
- Increase the Colab worker mix from `8:2` to `10:2`.
- Record the exact next source-selection and slice-planning targets.

## Deliverables

- [x] One notebook constant set for the large multi-session Colab slice.
- [x] One planned source-selection cap of `36,000` bounded `rixvox train` rows.
- [x] One planned Colab target slice of roughly `18,000` rows via
  `slice_count=2` and `slice_index=1`.
- [x] One completed task doc recording the exact next plan.

## Acceptance Criteria

- [x] The notebook defaults to the large multi-session slice identifiers.
- [x] The notebook defaults to a persistent `RUN_ROOT` under Google Drive.
- [x] The notebook defaults to `row_worker_count=10` and
  `gpu_asr_worker_count=2`.
- [x] The notebook timeout is long enough for a 10-hour Colab session.
- [x] The next plan keeps Colab on one fixed disjoint slice that can be resumed
  across multiple sessions.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
