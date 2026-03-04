---
id: task-69-add-page-level-progress-fields-to-v2-jobs-api
title: Add page-level progress fields to v2 jobs API
type: task
status: completed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-18-page-level-progress-and-stall-telemetry-contract.md
  - docs/backlog/tasks/task-67-detect-stalled-conversions-separately-from-active-long-running-jobs.md
  - docs/backlog/tasks/task-68-publish-adr-for-progress-checkpoint-and-resume-contract.md
  - scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_client_v2.py
  - scripts/sir_convert_a_lot/application/contracts_v2.py
labels:
  - long-pdf
  - api-contract
  - progress
  - telemetry
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Expose actionable page-level progress and stall metadata in the v2 jobs API for long PDF
conversions.

## PR Scope

- Extend contracts/models to include:
  - `total_pages`, `processed_pages`, `failed_pages`, `percent_complete`,
  - `pages_per_minute`, `eta_seconds`,
  - (stall classification is client-side; see `T67`).
- Populate these fields from runtime/job-store data during conversion lifecycle (best-effort).
- Update v2 lifecycle event payloads (SSE + webhooks) so progress is available without polling.

## Deliverables

- [x] API contract updates and implementation in v2 route + storage/runtime layers.
- [x] SSE + webhook parity for progress payload fields.
- [x] Tests for payload presence and compatibility behavior.

## Acceptance Criteria

- [x] API responses include page-level progress fields for PDF routes.
- [x] Progress values are monotonic and consistent with conversion state transitions.
- [x] Existing clients that ignore new fields continue to function unchanged.
- [x] SSE and webhook lifecycle progress payloads include the same progress fields as polling.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- Progress fields are stored in the v2 job-store manifest under `progress` and surfaced through:
  - polling: `GET /v2/convert/jobs/{job_id}`
  - SSE: `GET /v2/convert/jobs/{job_id}/events/stream`
  - webhooks: callback payloads now include `route` + `progress` for parity with SSE.
- `total_pages` is populated best-effort at the start of PDF execution via PyMuPDF metadata read.
- `percent_complete=100.0` and `eta_seconds=0` are set on PDF success.

## Validation Evidence (2026-03-04)

- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run pytest-root tests/sir_convert_a_lot` (pass: `419 passed, 5 skipped`)
- `pdm run coverage-gate` (pass: total coverage `95.39%`)
- `pdm run validate-tasks` (pass: `Validated 105 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=129 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
