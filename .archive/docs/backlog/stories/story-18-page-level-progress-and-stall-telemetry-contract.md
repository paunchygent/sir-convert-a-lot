---
id: story-18-page-level-progress-and-stall-telemetry-contract
title: Page-level progress and stall telemetry contract
type: story
status: completed
priority: high
created: '2026-03-04'
last_updated: '2026-03-05'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-17-progress-aware-timeout-for-long-running-conversion-jobs.md
  - docs/backlog/tasks/task-68-publish-adr-for-progress-checkpoint-and-resume-contract.md
  - docs/backlog/tasks/task-69-add-page-level-progress-fields-to-v2-jobs-api.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
  - scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_client_v2.py
labels:
  - long-pdf
  - progress-tracking
  - api-contract
  - telemetry
---

Implementation slice with acceptance-driven scope.

## Objective

Define and implement page-level progress semantics so operators and clients can see real conversion
progress (not only heartbeat) and distinguish active work from stalled work.

## Scope

- Publish ADR-backed contract for long-job progress/status semantics.
- Extend v2 job status payload with explicit progress fields for PDF routes, and define how they are
  represented for non-PDF routes (omitted or `null` by contract).
- Extend v2 lifecycle event progress payloads (SSE + webhooks) so progress visibility does not
  require polling.
- Progress fields must be monotonic and safe under retries/resume:
  - counters must be page-based for PDF routes (`total_pages`, `processed_pages`, `failed_pages`),
  - update cadence may be chunk-based (for example progress updates after each chunk completes).
- Update client polling behavior and manifest messaging so active jobs are not marked as failed.
- Keep backward compatibility for clients that only consume legacy status fields.

## Acceptance Criteria

- [x] Progress payload includes page-aware counters and ETA for PDF jobs.
- [x] Active long jobs with fresh progress updates never surface as failure-like timeout states.
- [x] Stalled jobs are deterministically classified with explicit reason code/details.
- [x] CLI/manifest output clearly differentiates:
  - active-running long jobs,
  - stalled-timeout jobs,
  - terminal failed jobs.
- [x] SSE and webhook progress payloads are upgraded in lockstep with polling payloads.

## Test Requirements

- [x] Unit tests for progress and stall classification calculations.
- [x] API contract tests for new progress fields and compatibility behavior.
- [x] CLI polling/manifest tests for active vs stalled timeout mapping.
- [x] Regression tests to prove non-PDF routes are unaffected.

## Done Definition

Page-level progress is visible and reliable enough for operators to make informed cancel/continue
decisions on long PDF OCR jobs without ambiguity.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
