---
id: task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics
title: Add conversion bottleneck telemetry and stage timing metrics
type: task
status: proposed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_api.py
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
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
- Add GPU/acceleration evidence fields suitable for production tuning:
  - acceleration policy requested/used (or equivalent job metadata),
  - GPU utilization snapshot fields (ROCm equivalent when applicable) and any explicit GPU
    concurrency-cap signals.
- Ensure metrics can be correlated with job id and conversion profile.
- Update dashboards/runbook sections for interpreting these metrics.

## Deliverables

- [ ] New metrics/timing instrumentation in runtime pipeline.
- [ ] Exposed metrics endpoint fields and docs updates.
- [ ] Tests validating timing/metric emission for success and failure paths.
- [ ] Runbook section for bottleneck triage workflow.

## Acceptance Criteria

- [ ] Each long PDF job produces stage-timing evidence sufficient for bottleneck diagnosis.
- [ ] Metrics expose queue/worker saturation for parallel mode tuning.
- [ ] Metrics remain stable and low-overhead under production load.
- [ ] Operators can trace top slowdown source from metrics and logs deterministically.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
