---
id: task-68-publish-adr-for-progress-checkpoint-and-resume-contract
title: Publish ADR for progress checkpoint and resume contract
type: task
status: completed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-18-page-level-progress-and-stall-telemetry-contract.md
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/tasks/task-67-detect-stalled-conversions-separately-from-active-long-running-jobs.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
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

- [x] ADR document with accepted status and explicit contract tables.
- [x] Updated links in `docs/converters/multi_format_conversion_service_api_v2.md`.
- [x] Backlog cross-references synchronized.

## Acceptance Criteria

- [x] ADR is implementation-grade and unambiguous for API/runtime/CLI teams.
- [x] ADR includes migration/compatibility guidance for existing polling clients.
- [x] ADR is linked from all dependent stories/tasks.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- Published ADR: `docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md`.
- Linked ADR from `docs/converters/multi_format_conversion_service_api_v2.md` and dependent backlog items.

## Validation Evidence (2026-03-04)

- `pdm run validate-tasks` (pass: `Validated 105 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=129 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
