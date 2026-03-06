---
id: task-74-run-throughput-benchmark-and-publish-performance-tuning-report
title: Run throughput benchmark and publish performance tuning report
type: task
status: in_progress
priority: high
created: '2026-03-04'
last_updated: '2026-03-06'
related:
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - docs/backlog/tasks/task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/benchmark_story20_throughput_report.py
  - scripts/sir_convert_a_lot/benchmarking/story20_throughput_report.py
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

## Status Update (2026-03-06)

- Implemented the Task 74 benchmark/report command surface:
  - `pdm run benchmark:task-74`
  - benchmark harness: `scripts/sir_convert_a_lot/benchmark_story20_throughput_report.py`
  - markdown report writer: `scripts/sir_convert_a_lot/benchmarking/story20_throughput_report.py`
- The harness now:
  - generates representative scanned-PDF corpus files,
  - runs baseline and tuned runtime profiles through the v2 API/runtime path,
  - captures p50/p90 latency, success/error rates, queue/worker saturation, and GPU gauges,
  - emits JSON + markdown artifacts under `build/benchmarks/story-20/`.
- Added regression coverage:
  - `tests/sir_convert_a_lot/test_benchmark_story20_throughput_report.py`
- Local smoke command completed on laptop using CPU-only overrides:
  - `build/benchmarks/story-20/task-74-throughput-smoke-local.json`
  - `build/benchmarks/story-20/task-74-throughput-smoke-local.md`
- Live Hemma evidence is still pending:
  - current local `HEAD`: `855b5a46f8640b69112e9cd1ad071f4f94ea17f1`
  - current deployed `/healthz.service_revision`: `e7a1e38c1e73ab9cd7953f68560c8e82df8d88ac`
  - Task 76 deploy-parity gate must be rerun on a pushed revision before the final Hemma benchmark/report pass.

## Validation Evidence

- `pdm run typecheck-all` (pass: `Success: no issues found in 211 source files`)
- `pdm run pytest-root tests/sir_convert_a_lot/test_benchmark_story20_parallel_throughput.py tests/sir_convert_a_lot/test_benchmark_story20_telemetry_overhead.py tests/sir_convert_a_lot/test_benchmark_story20_throughput_report.py -q` (pass: `9 passed`)
- Local smoke command (pass for command surface; not acceptance evidence):
  - `pdm run benchmark:task-74 --page-counts 2,3 --acceleration-policy cpu_only --ocr-mode off --ocr-engine auto --ocr-languages en --no-gpu-available --max-poll-seconds 120 --output-json build/benchmarks/story-20/task-74-throughput-smoke-local.json --output-report build/benchmarks/story-20/task-74-throughput-smoke-local.md --corpus-root build/benchmarks/story-20/task-74-smoke-corpus --data-root build/benchmarks/story-20/task-74-smoke-runtime`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
