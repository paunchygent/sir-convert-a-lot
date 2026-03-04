---
id: 'task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools'
title: 'Parallelize PDF OCR conversion with bounded worker pools'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - long-pdf
  - performance
  - parallelization
  - worker-pool
  - gpu
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Increase throughput for long OCR jobs by processing chunks with bounded parallel workers while
preserving determinism and system stability.

## PR Scope

- Introduce bounded worker pool controls for PDF chunk conversion.
- Add scheduler logic for chunk dispatch and ordered merge semantics.
- Add configuration knobs for worker count/chunk size with safe defaults.
- Guard against GPU memory oversubscription and runaway CPU contention.

## Deliverables

- [ ] Parallel execution implementation in runtime/conversion pipeline.
- [ ] Config surface for pool size and chunk strategy.
- [ ] Concurrency safety tests and deterministic output tests.
- [ ] Updated runbook guidance for production tuning.

## Acceptance Criteria

- [ ] Parallel mode improves throughput on benchmark long-PDF corpus.
- [ ] Output remains deterministic versus serial baseline.
- [ ] Runtime remains stable under concurrent long-job load.
- [ ] Worker pool defaults are documented and safe for Hemma profile.
- [ ] GPU-backed stages are explicitly capped to avoid OOM/thrash, and GPU policy enforcement remains
      intact (no silent CPU fallback when GPU is requested/required).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
