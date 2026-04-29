---
id: task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics
title: Add conversion bottleneck telemetry and stage timing metrics
type: task
status: completed
priority: high
created: '2026-03-04'
last_updated: '2026-04-29'
related:
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_api.py
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/reference/ref-task-73-telemetry-overhead-evidence.md
labels:
  - observability
  - performance
  - telemetry
  - bottlenecks
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Expose stage-level timings and utilization metrics so real bottlenecks can be identified and removed
instead of tuning blindly.

## PR Scope

- Add per-stage timers for:
  - OCR,
  - layout/structure extraction,
  - markdown normalization,
  - checkpoint persist/final artifact persist.
- Add metrics for chunk queue depth, worker saturation, and retry counts.
- Define canonical v2 timing keys and enforce canonical-only persistence/merge rules at manifest
  merge points.
- Add GPU/acceleration evidence fields suitable for production tuning:
  - acceleration policy requested/used (or equivalent job metadata),
  - GPU utilization snapshot fields (ROCm equivalent when applicable) and any explicit GPU
    concurrency-cap signals.
- Ensure metrics use bounded-cardinality labels only:
  - never use `job_id`, correlation id, filename, or dynamic route values as metric labels,
  - correlate per-job investigations through logs/events (`X-Correlation-ID`, SSE/webhook/event
    payloads).
- Add explicit telemetry sink ownership in app state and inject the sink into runtime services.
- Update dashboards/runbook sections for interpreting these metrics.

## Deliverables

- [x] New metrics/timing instrumentation in runtime pipeline.
- [x] Exposed metrics endpoint fields and docs updates.
- [x] Tests validating timing/metric emission for success and failure paths.
- [x] Runbook section for bottleneck triage workflow.

## Acceptance Criteria

- [x] Each long PDF job produces stage-timing evidence sufficient for bottleneck diagnosis.
- [x] Metrics expose queue/worker saturation for parallel mode tuning.
- [x] Metrics remain stable and low-overhead under production load.
- [x] Operators can trace top slowdown source from metrics and logs deterministically.

## Status Update (2026-03-05)

- Implemented:
  - canonical timing key enforcement + merge-point enforcement,
  - bounded runtime telemetry metrics and sink injection ownership in app state,
  - contract/runbook updates for label-cardinality safety and timing key policy,
  - regression tests for canonical timing normalization and no-`job_id` metric labels,
  - success/failure-path metrics contract tests (`/metrics` label safety + terminal counters),
  - acceleration policy + GPU utilization snapshot fields in `result.conversion_metadata`,
  - synthetic sustained-load overhead regression evidence:
    - `build/benchmarks/story-20/task-73-telemetry-overhead-local.json`
    - benchmark id: `task-73-telemetry-overhead`,
    - run sample (`2026-03-05`): `overhead_percent.full_vs_sink_disabled=1.3728%`,
      `overhead_percent.full_vs_bypassed=-1.4069%`, bounded labels verified.
    - this local artifact is telemetry implementation evidence only; it must not be cited as
      production performance proof, throughput proof, tuning evidence, acceptance evidence, or a
      reason to set Hemma production defaults.
  - benchmark contract hardened with strict canonical fields:
    - removed deprecated field `telemetry_overhead_percent`,
    - retained explicit mode-only overhead keys.

## Ruthless Review Findings (2026-03-05)

- High:
  - success-path GPU snapshot collection can fail terminal success transitions:
    - current flow collects GPU snapshot before `mark_succeeded`,
    - exceptions can route to generic failure handling and incorrectly fail otherwise successful jobs.
- Medium:
  - telemetry overhead benchmark compares Prometheus sink on/off, not full telemetry pipeline on/off:
    - this can over-claim/under-claim true end-to-end telemetry overhead.
- Medium:
  - missing regression proving GPU snapshot collection failures remain non-fatal for successful jobs.

## Suggested Remediation Approach

1. Make GPU snapshot enrichment fail-open:
   - wrap snapshot collection in dedicated `try/except`,
   - bound subprocess calls with explicit timeout,
   - persist `null` snapshot fields + warning instead of flipping job state.
1. Split benchmark modes for defensible overhead evidence:
   - mode A: full telemetry enabled,
   - mode B: sink-only disabled (current),
   - mode C: telemetry calls fully bypassed in runtime hot paths.
1. Add targeted regressions:
   - success-path test where GPU snapshot helper raises and job still succeeds,
   - timeout test for snapshot subprocess path (rocm/nvidia) with non-fatal outcome.
1. Update runbook and reference evidence:
   - clearly label benchmark mode and what is measured,
   - record acceptable overhead threshold with rationale.

## Remediation Checklist (Reopen Scope)

- [x] GPU snapshot collection cannot change successful job outcome to failed.
- [x] Snapshot subprocess calls are timeout-bounded.
- [x] Benchmark report distinguishes sink-only vs full telemetry overhead.
- [x] New non-fatal snapshot regression tests are added and passing.
- [x] Acceptance criteria above are re-evaluated and terminalized after fixes.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
