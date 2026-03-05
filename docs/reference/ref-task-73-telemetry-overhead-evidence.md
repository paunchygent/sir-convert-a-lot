---
type: reference
id: REF-task-73-telemetry-overhead-evidence
title: Task 73 Telemetry Overhead Evidence
status: active
created: '2026-03-05'
updated: '2026-03-05'
owners:
  - platform
tags:
  - benchmark
  - telemetry
  - observability
  - performance
links:
  - docs/backlog/tasks/task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics.md
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - build/benchmarks/story-20/task-73-telemetry-overhead-local.json
---

## Purpose

Capture deterministic synthetic load evidence for Task 73 to quantify telemetry overhead and confirm
bounded-cardinality metric behavior under sustained queued-job execution.

## Benchmark Command

```bash
pdm run benchmark:task-73-telemetry \
  --total-jobs 40 \
  --max-workers 8 \
  --stub-work-seconds 0.2 \
  --output-json build/benchmarks/story-20/task-73-telemetry-overhead-local.json \
  --data-root build/benchmarks/story-20/task-73-telemetry-runtime
```

## Latest Local Run (2026-03-05)

Artifact:

- `build/benchmarks/story-20/task-73-telemetry-overhead-local.json`

Config:

- `total_jobs`: `40`
- `max_workers`: `8`
- `stub_work_seconds`: `0.2`

Result summary:

- `overhead_percent.full_vs_sink_disabled`: `1.3728`
- `overhead_percent.full_vs_bypassed`: `-1.4069`
- `telemetry_full.duration_seconds`: `3.800695`
- `telemetry_sink_disabled.duration_seconds`: `3.749225`
- `telemetry_calls_bypassed.duration_seconds`: `3.854929`
- `telemetry_full.throughput_jobs_per_minute`: `631.463394`
- `telemetry_sink_disabled.throughput_jobs_per_minute`: `640.132372`
- `telemetry_calls_bypassed.throughput_jobs_per_minute`: `622.579607`
- `telemetry_full.metrics_summary.contains_job_id_label`: `false`
- `telemetry_full.metrics_summary.terminal_job_samples`: `40.0`
- `telemetry_full.metrics_summary.stage_duration_samples`: `160.0`
- `telemetry_full.metrics_summary.worker_saturation_peak`: `0.625`
- `telemetry_full.metrics_summary.gpu_concurrency_cap`: `8.0`

## Interpretation

- Sink-only overhead and full-bypass overhead are now reported separately.
- This run shows low overhead for full telemetry vs sink-disabled mode (~`1.37%`).
- Full vs bypassed was negative in this run (`-1.41%`), which indicates normal synthetic benchmark
  noise rather than a guaranteed speedup.
- Stage timing and terminal counters emitted expected sample counts.
- Worker saturation and concurrency-cap telemetry were visible for bottleneck triage workflows.
