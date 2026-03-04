---
id: 'task-68-publish-adr-for-progress-checkpoint-and-resume-contract'
title: 'Publish ADR for progress checkpoint and resume contract'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-18-page-level-progress-and-stall-telemetry-contract.md
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/tasks/task-67-detect-stalled-conversions-separately-from-active-long-running-jobs.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
labels:
  - adr
  - long-pdf
  - progress-contract
  - checkpoint-contract
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish a decision record that locks long-job progress, partial artifact, cancel-with-save, and
resume semantics before implementation changes.

## PR Scope

- Add new ADR defining:
  - page-aware progress payload fields,
  - stall vs active timeout classification,
  - checkpoint artifact storage and lifecycle,
  - partial artifact retrieval semantics,
  - cancel-with-save and resume behavior.
- Link ADR to epic/story/task chain and v2 API docs.
- Define backward-compatibility policy for existing clients.

## Deliverables

- [ ] ADR document with accepted status and explicit contract tables.
- [ ] Updated links in `docs/converters/multi_format_conversion_service_api_v2.md`.
- [ ] Backlog cross-references synchronized.

## Acceptance Criteria

- [ ] ADR is implementation-grade and unambiguous for API/runtime/CLI teams.
- [ ] ADR includes migration/compatibility guidance for existing polling clients.
- [ ] ADR is linked from all dependent stories/tasks.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
