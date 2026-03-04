---
id: 'task-67-detect-stalled-conversions-separately-from-active-long-running-jobs'
title: 'Detect stalled conversions separately from active long-running jobs'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-17-progress-aware-timeout-for-long-running-conversion-jobs.md
  - scripts/sir_convert_a_lot/interfaces/http_client_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_client.py
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

- [ ] v2 client timeout classification implementation with explicit stale threshold.
- [ ] CLI manifest semantics update for running-vs-stalled timeout handling.
- [ ] Regression tests for classification and manifest behavior.
- [ ] Documentation update in converter/client docs describing the semantics.

## Acceptance Criteria

- [ ] Active long-running jobs never produce misleading `job_timeout` failure semantics.
- [ ] Stalled jobs produce deterministic stall-timeout classification with actionable message.
- [ ] Existing successful/failed/canceled polling flows remain unchanged.
- [ ] New and updated tests pass in local quality gates.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
