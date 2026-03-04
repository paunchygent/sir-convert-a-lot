---
id: 'task-69-add-page-level-progress-fields-to-v2-jobs-api'
title: 'Add page-level progress fields to v2 jobs API'
type: 'task'
status: 'proposed'
priority: 'high'
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
  - `progress_freshness` and stall classification reason fields.
- Populate these fields from runtime/job-store data during conversion lifecycle.
- Update v2 lifecycle event payloads (SSE + webhooks) so progress is available without polling.
- Update CLI polling/manifest mapping for active-running vs stalled-timeout behavior.

## Deliverables

- [ ] API contract updates and implementation in v2 route + client layers.
- [ ] CLI/manifest mapping update for progress-aware semantics.
- [ ] Tests for payload presence, compatibility, and timeout classification behavior.

## Acceptance Criteria

- [ ] API responses include page-level progress fields for PDF routes.
- [ ] Progress values are monotonic and consistent with conversion state transitions.
- [ ] Stalled jobs and active jobs are classified distinctly and deterministically.
- [ ] Existing clients that ignore new fields continue to function unchanged.
- [ ] SSE and webhook lifecycle progress payloads include the same progress/stall fields as polling.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
