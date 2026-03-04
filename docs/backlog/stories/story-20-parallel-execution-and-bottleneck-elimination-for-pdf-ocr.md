---
id: story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr
title: Parallel execution and bottleneck elimination for PDF OCR
type: story
status: proposed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - docs/backlog/tasks/task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
labels:
  - long-pdf
  - performance
  - bottlenecks
  - parallelization
  - gpu
---

Implementation slice with acceptance-driven scope.

## Objective

Reduce wall-clock conversion time and increase predictability for long OCR jobs by introducing
bounded parallel execution and evidence-driven bottleneck removal.

## Scope

- Implement bounded parallel worker pools for chunk/page processing where safe.
- Add scheduling controls to avoid GPU/CPU over-subscription and memory contention.
- Instrument stage timings and resource telemetry for OCR/layout/normalization/persist phases.
- Produce benchmark baselines and tuned profiles for long scanned PDFs on Hemma hardware.
- Publish runbook recommendations for worker counts, chunk sizes, and fallback strategy.

Guardrails:

- Parallelization is opt-in behind config defaults until benchmark evidence exists.
- GPU-backed stages must have explicit concurrency caps to avoid OOM and thrash.
- Any backend-specific limitations (Docling vs PyMuPDF) must be captured in the benchmark report.

## Acceptance Criteria

- [ ] Throughput improvements are measurable and reproducible on benchmark corpus.
- [ ] Median wall-clock for long scanned OCR jobs improves by >= 40% from baseline.
- [ ] Telemetry identifies top bottlenecks with stage-level timings and utilization evidence.
- [ ] Parallelization does not regress output determinism or API contract behavior.
- [ ] GPU-first governance remains enforced under parallel mode (no silent CPU fallback, explicit
  concurrency caps for GPU-backed stages).

## Test Requirements

- [ ] Concurrency safety tests for worker pool execution and checkpoint writes.
- [ ] Regression tests for deterministic markdown output under parallel mode.
- [ ] Benchmark harness test run producing machine-readable report artifacts.
- [ ] Load tests validating stability under multiple long-running jobs.

## Done Definition

Long PDF OCR conversion performance is tuned with clear bottleneck evidence, robust parallel
execution controls, and documented operational defaults for production use.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
