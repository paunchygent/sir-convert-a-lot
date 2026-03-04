---
id: story-17-progress-aware-timeout-for-long-running-conversion-jobs
title: Progress-aware timeout for long-running conversion jobs
type: story
status: completed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/tasks/task-67-detect-stalled-conversions-separately-from-active-long-running-jobs.md
  - scripts/sir_convert_a_lot/interfaces/http_client_v2.py
  - scripts/sir_convert_a_lot/interfaces/cli_app.py
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - timeout-governance
  - async-jobs
  - cli-manifest
---

Implementation slice with acceptance-driven scope.

## Objective

Ensure client-facing timeout behavior distinguishes between:

- active long-running conversions (progressing and heartbeating), and
- truly stalled conversions (no meaningful progress/heartbeat for a bounded window).

This prevents false-failure signals (`job_timeout`) for large OCR/ML jobs that are still healthy.

## Scope

- Introduce stall-aware timeout classification in v2 HTTP client polling logic.
- Define explicit stale-progress/stale-heartbeat thresholds for terminal timeout classification.
- Keep current async contract intact (`status=running` for active jobs) while improving manifest/error
  semantics.
- Document operator-facing behavior and triage guidance.

Compatibility constraint:

- If page-level progress fields are not yet present (or are `null`) in the v2 job payload, stall
  classification must fall back to heartbeat freshness only. This story must not be blocked on
  Story 18.

## Acceptance Criteria

- [x] A long-running conversion that keeps updating heartbeat/progress does not produce a
  failure-like timeout classification.
- [x] A stalled conversion (no heartbeat/progress past threshold) is classified deterministically
  with a dedicated stall timeout error code.
- [x] CLI manifest semantics are explicit:
  - active-but-not-finished jobs remain `status=running` with non-failure messaging,
  - stall timeout entries are clearly distinguishable from active-running entries.
- [x] Converter docs describe the new timeout taxonomy and recommended polling/fetch flow.
- [x] When progress fields are absent/`null`, the client still behaves correctly using heartbeat-only
  freshness semantics (no false stall classification).

## Test Requirements

- [x] Unit tests for heartbeat/progress-aware timeout classification logic in v2 client polling.
- [x] CLI behavior tests for manifest entries and console output around running vs stalled jobs.
- [x] Contract-level regression test: active heartbeat through max poll window does not map to
  failure-like timeout.

## Done Definition

Story is done when timeout semantics are progress-aware, tested, and documented so large conversions
can safely exceed client wait windows without misleading failure labels.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
