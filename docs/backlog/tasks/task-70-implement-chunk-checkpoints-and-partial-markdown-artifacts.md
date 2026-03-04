---
id: task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts
title: Implement chunk checkpoints and partial markdown artifacts
type: task
status: proposed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/tasks/task-68-publish-adr-for-progress-checkpoint-and-resume-contract.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
  - scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py
  - scripts/sir_convert_a_lot/infrastructure/job_store_v2.py
labels:
  - long-pdf
  - checkpoints
  - partial-results
  - runtime
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Persist conversion output incrementally so long jobs can expose partial markdown artifacts before
terminal completion.

## PR Scope

- Implement chunk-based processing checkpoints for PDF OCR conversions.
- Persist chunk metadata (page range, status, timings, artifact path, checksum).
- Produce deterministic partial markdown artifact assembly from completed chunks.
- Expose partial artifact metadata through job store/runtime contract.
- Add bounded-retention behavior for checkpoint artifacts:
  - define TTL/pinning semantics for partials and checkpoints,
  - implement cleanup triggers (on terminalization and/or scheduled cleanup) to prevent disk fill.
- Define and implement partial artifact retrieval semantics:
  - either a new v2 endpoint, or a query-param variant on the existing `artifact` endpoint,
  - explicit status-code semantics for `running`, `canceled`, `failed`, and `succeeded` states.

## Deliverables

- [ ] Runtime + job-store checkpoint implementation.
- [ ] Partial markdown artifact output contract and storage layout.
- [ ] Tests for chunk persistence, ordering, and artifact merge determinism.

## Acceptance Criteria

- [ ] Checkpoints are written incrementally during long-running conversions.
- [ ] Partial artifact is retrievable and valid while job status remains `running`.
- [ ] Crash/restart can recover completed chunks without data loss.
- [ ] Final merged artifact is deterministic regardless of partial retrieval timing.
- [ ] Partial/checkpoint retention is bounded and documented (no unbounded disk growth under repeated
  long conversions).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
