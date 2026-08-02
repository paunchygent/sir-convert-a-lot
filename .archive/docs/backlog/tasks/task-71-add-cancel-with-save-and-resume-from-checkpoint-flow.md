---
id: task-71-add-cancel-with-save-and-resume-from-checkpoint-flow
title: Add cancel-with-save and resume-from-checkpoint flow
type: task
status: completed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/tasks/task-68-publish-adr-for-progress-checkpoint-and-resume-contract.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_client_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_client_v2_polling.py
  - scripts/sir_convert_a_lot/interfaces/http_routes_job_resume_v2.py
  - scripts/sir_convert_a_lot/interfaces/cli_jobs_v2.py
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py
  - scripts/sir_convert_a_lot/infrastructure/pdf_resume_v2.py
  - tests/sir_convert_a_lot/test_api_contract_v2_pdf_cancel_and_resume.py
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
  - dedicated resume endpoint: `POST /v2/convert/jobs/{job_id}/resume`,
  - resume requires `Idempotency-Key` and must be idempotent (no duplicate resumed jobs for the same
    key + source job + checkpoint).
- Resume semantics must be explicit:
  - resume creates a new job id (do not mutate the original job record/artifact),
  - resumed job must reference the source job id/checkpoint in stored metadata for auditability.
- Ensure resumed execution skips completed chunks/pages and appends only missing output.
- Update CLI to support resume flow and partial artifact retrieval UX.

## Deliverables

- [x] Cancel-with-save implementation with deterministic artifact semantics.
- [x] Resume-from-checkpoint API/runtime implementation.
- [x] CLI flags/flow for resume and partial artifact retrieval.
- [x] Integration tests for cancel->resume lifecycle.

## Acceptance Criteria

- [x] Canceling long job preserves completed output and exposes it predictably.
- [x] Resumed job restarts from checkpoint, not from page one.
- [x] Final artifact from resumed flow matches deterministic full-run baseline.
- [x] Duplicate content is prevented across cancel/resume boundaries.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- Cancel-with-save stops chunk execution at safe boundaries and preserves checkpoint/partials.
- `POST /v2/convert/jobs/{job_id}/resume` creates a new job id and clones checkpoint state.
- Resume is idempotent per `(api_key, source_job_id, Idempotency-Key)` with request fingerprinting.

## Validation Evidence (2026-03-04)

- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run pytest-root tests/sir_convert_a_lot` (pass)
- `pdm run coverage-gate` (pass)
- `pdm run validate-tasks` (pass)
- `pdm run validate-docs` (pass)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
