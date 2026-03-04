---
id: task-67-detect-stalled-conversions-separately-from-active-long-running-jobs
title: Detect stalled conversions separately from active long-running jobs
type: task
status: completed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-17-progress-aware-timeout-for-long-running-conversion-jobs.md
  - scripts/sir_convert_a_lot/interfaces/http_client_v2.py
  - scripts/sir_convert_a_lot/interfaces/cli_app.py
labels:
  - timeout-governance
  - async-jobs
  - client-polling
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement stall-aware polling timeout semantics so the client only emits terminal timeout errors when
jobs stop progressing, not when they are still actively converting beyond the local wait window.

## PR Scope

- Add timeout classification helper that inspects heartbeat/progress freshness while polling job
  status.
- Ensure compatibility while Story 18 is pending:
  - if page-level progress fields are absent/`null`, classify freshness using heartbeat-only
    semantics,
  - never require page-level fields for this task to be complete.
- Return active-running outcome when:
  - job status is `running`, and
  - heartbeat/progress remains fresh within configured stall threshold.
- Emit a dedicated stall timeout error only when running-job freshness exceeds the threshold.
- Update CLI manifest/error mapping so active-running and stalled-timeout states are not conflated.

## Deliverables

- [x] v2 client timeout classification implementation with explicit stale threshold.
- [x] CLI manifest semantics update for running-vs-stalled timeout handling.
- [x] Regression tests for classification and manifest behavior.
- [x] Documentation update in converter/client docs describing the semantics.

## Acceptance Criteria

- [x] Active long-running jobs never produce misleading `job_timeout` failure semantics.
- [x] Stalled jobs produce deterministic stall-timeout classification with actionable message.
- [x] Existing successful/failed/canceled polling flows remain unchanged.
- [x] New and updated tests pass in local quality gates.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- Active-running poll window exceeded is now emitted as `ClientError(code="job_poll_window_exceeded")`.
- `ClientError(code="job_timeout")` is reserved for stale heartbeat/progress classification (likely stalled).
- Added CLI option `--stall-timeout-seconds` to control stale detection threshold.

## Validation Evidence (2026-03-04)

- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass: `Success: no issues found in 168 source files`)
- `pdm run pytest-root tests/sir_convert_a_lot` (pass: `419 passed, 5 skipped`)
- `pdm run coverage-gate` (pass: `Required test coverage of 90.0% reached. Total coverage: 95.29%`)
- `pdm run validate-tasks` (pass: `Validated 105 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=128 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
