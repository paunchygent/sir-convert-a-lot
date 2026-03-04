---
id: task-74-run-throughput-benchmark-and-publish-performance-tuning-report
title: Run throughput benchmark and publish performance tuning report
type: task
status: proposed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - docs/backlog/tasks/task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/benchmarking/scientific_corpus_report.py
labels:
  - benchmarking
  - performance
  - tuning
  - long-pdf
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Produce reproducible performance evidence and recommended runtime defaults for long scanned PDF OCR
conversions on Hemma.

## PR Scope

- Define benchmark corpus representative of 100-300+ page scanned textbook workloads.
- Run baseline vs tuned profiles (serial, parallel worker configs, chunk-size variants).
- Capture throughput, wall-clock, error rate, GPU utilization, and stage timing metrics.
- Publish tuning report and operational defaults in runbook form.

Measurement rules (must be explicit in report):

- Primary metric: wall-clock time from `created_at` to terminal `succeeded` for `pdf -> md` jobs.
- Report percentiles at minimum: p50 and p90, with N documented.
- Include resource evidence:
  - worker pool saturation and queue depth metrics,
  - GPU busy/utilization snapshot for the run (ROCm equivalent when applicable),
  - peak memory notes when available.

## Deliverables

- [ ] Benchmark execution artifacts (raw results + summary tables/plots).
- [ ] Written tuning report with recommended defaults and guardrails.
- [ ] Updated runbook section with production settings and rollback criteria.
- [ ] Acceptance evidence linked from epic/story/task docs.

## Acceptance Criteria

- [ ] Benchmark report is reproducible with documented command surface and dataset profile.
- [ ] Tuned profile demonstrates >= 40% median runtime improvement vs baseline.
- [ ] Recommended defaults include explicit safety limits (workers/chunk size/memory).
- [ ] Report includes rollback path when runtime conditions deviate from benchmark assumptions.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
