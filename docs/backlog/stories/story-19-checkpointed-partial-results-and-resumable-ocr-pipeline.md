---
id: story-19-checkpointed-partial-results-and-resumable-ocr-pipeline
title: Checkpointed partial results and resumable OCR pipeline
type: story
status: proposed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - docs/backlog/tasks/task-71-add-cancel-with-save-and-resume-from-checkpoint-flow.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
  - scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py
  - scripts/sir_convert_a_lot/infrastructure/job_store_v2.py
labels:
  - long-pdf
  - checkpoints
  - partial-results
  - resume
---

Implementation slice with acceptance-driven scope.

## Objective

Enable safe interruption and recovery for long OCR conversions by writing deterministic checkpoints
and partial markdown artifacts throughout execution.

## Scope

- Introduce chunk-level processing model for long PDFs (for example fixed page windows).
- Persist checkpoint metadata and intermediate markdown chunks in job storage.
- Add partial artifact retrieval contract for running/canceled jobs.
- Add cancel-with-save behavior that finalizes and exposes completed chunks.
- Add resume-from-checkpoint behavior that skips already completed chunks/pages.
- Ensure final artifact assembly remains deterministic and idempotent.
- Define retention/cleanup policy so partial artifacts and checkpoints do not create unbounded disk
  growth (TTL, pinning rules, and cleanup triggers must be explicit).

Non-goals and constraints (must be documented in the ADR and tests):

- Chunk boundaries can degrade cross-page structures (tables, figures, running headers).
- Mitigation strategy must be explicit:
  - chunk size defaults tuned for scanned textbooks,
  - merge rules that preserve section ordering and avoid duplicate headings,
  - known limitations called out in converter docs.

## Acceptance Criteria

- [ ] Running jobs can expose partial markdown artifacts and checkpoint metadata.
- [ ] Canceling a long job preserves completed chunks and marks partial output as retrievable.
- [ ] Resumed job continues from latest valid checkpoint with no duplicate output sections.
- [ ] Final merged markdown from resumed run is deterministic and structurally valid.
- [ ] Partial outputs have a stable on-disk layout and stable API retrieval semantics.

## Test Requirements

- [ ] Integration tests for chunk checkpoint persistence and recovery.
- [ ] API tests for partial artifact retrieval in running/canceled states.
- [ ] End-to-end tests for cancel-then-resume flow producing stable final artifact.
- [ ] Failure injection tests for restart/recovery after process interruption.

## Done Definition

Long conversions are no longer all-or-nothing: users can stop safely, keep work completed so far,
and resume without restarting OCR from page one.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
