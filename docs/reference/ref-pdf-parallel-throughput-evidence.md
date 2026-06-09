---
type: reference
id: REF-pdf-parallel-throughput-evidence
title: PDF Parallel Throughput Evidence
status: active
created: '2026-03-06'
updated: '2026-03-06'
owners:
  - platform
tags:
  - benchmark
  - performance
  - parallelization
  - pdf
links:
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - build/benchmarks/pdf-throughput/pdf-parallel-throughput-local.json
---

## Purpose

Capture deterministic local throughput evidence for bounded parallel PDF chunk execution so Story 20 can treat bounded parallel
PDF chunk execution as implemented and benchmark-backed before the Hemma tuning/report slice in
Task 74.

## Benchmark Command

```bash
pdm run benchmark:pdf-parallel-throughput \
  --total-pages 8 \
  --repeats 5 \
  --chunk-size-pages 1 \
  --max-chunk-workers 4 \
  --stub-work-seconds 0.03 \
  --output-json build/benchmarks/pdf-throughput/pdf-parallel-throughput-local.json \
  --data-root build/benchmarks/pdf-throughput/pdf-parallel-throughput-runtime
```

## Latest Local Run (2026-03-06)

Artifact:

- `build/benchmarks/pdf-throughput/pdf-parallel-throughput-local.json`

Config:

- `total_pages`: `8`
- `repeats`: `5`
- `chunk_size_pages`: `1`
- `max_chunk_workers`: `4`
- `stub_work_seconds`: `0.03`

Result summary:

- `comparison.p50_wall_clock_improvement_percent`: `73.274`
- `comparison.byte_identical_to_serial`: `true`
- `serial.p50_duration_seconds`: `0.317518`
- `parallel.p50_duration_seconds`: `0.08486`
- `serial.result_metadata.parallel_enabled`: `false`
- `parallel.result_metadata.parallel_enabled`: `true`
- `parallel.result_metadata.scheduling_mode`: `parallel_ordered_commit`
- `parallel.result_metadata.effective_gpu_stage_limit`: `4`

## Interpretation

- This benchmark intentionally uses a deterministic stubbed chunk conversion path so the measured
  delta reflects PDF parallel throughput scheduling/commit overhead rather than OCR-model variability.
- Parallel output remained byte-identical to the serial baseline across the benchmark run.
- The observed p50 wall-clock reduction (`73.274%`) comfortably exceeds the PDF parallel throughput acceptance bar
  of `>= 10%` on the task fixture.
- This artifact is local implementation evidence only; Hemma production-profile defaults and
  rollback guidance remain the responsibility of Task 74.
