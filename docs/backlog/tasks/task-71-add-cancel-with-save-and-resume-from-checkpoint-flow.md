---
id: 'task-71-add-cancel-with-save-and-resume-from-checkpoint-flow'
title: 'Add cancel-with-save and resume-from-checkpoint flow'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/tasks/task-68-publish-adr-for-progress-checkpoint-and-resume-contract.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_client_v2.py
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
labels:
  - long-pdf
  - cancel-with-save
  - resume
  - checkpoints
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Support safe interruption and continuation for long OCR jobs by finalizing partial outputs on cancel
and allowing resume from last valid checkpoint.

## PR Scope

- Extend cancel endpoint/runtime path to persist and expose completed partial output.
- Add resume request path:
  - either `resume_from_job_id` in `JobSpecV2`, or a dedicated resume endpoint,
  - idempotency rules must be explicit (resume requests must not duplicate work).
- Resume semantics must be explicit:
  - resume creates a new job id (do not mutate the original job record/artifact),
  - resumed job must reference the source job id/checkpoint in stored metadata for auditability.
- Ensure resumed execution skips completed chunks/pages and appends only missing output.
- Update CLI to support resume flow and partial artifact retrieval UX.

## Deliverables

- [ ] Cancel-with-save implementation with deterministic artifact semantics.
- [ ] Resume-from-checkpoint API/runtime implementation.
- [ ] CLI flags/flow for resume and partial artifact retrieval.
- [ ] Integration tests for cancel->resume lifecycle.

## Acceptance Criteria

- [ ] Canceling long job preserves completed output and exposes it predictably.
- [ ] Resumed job restarts from checkpoint, not from page one.
- [ ] Final artifact from resumed flow matches deterministic full-run baseline.
- [ ] Duplicate content is prevented across cancel/resume boundaries.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
