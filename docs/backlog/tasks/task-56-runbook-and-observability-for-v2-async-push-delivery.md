---
id: 'task-56-runbook-and-observability-for-v2-async-push-delivery'
title: 'Runbook and observability for v2 async push delivery'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - runbook
  - observability
  - v2
  - async-push
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Operationalize v2 async push delivery with production runbooks, monitoring, alerting, and rollback
procedures.

## PR Scope

- Add/extend runbook guidance for async push operations:
  - event emission checks,
  - webhook delivery queue and retry triage,
  - DLQ handling and replay procedures,
  - incident response workflow.
- Define observability contract for push:
  - metrics,
  - traces,
  - structured logs,
  - dashboard views and alert thresholds,
  - baseline and target KPI calculation method.
- Document rollout/canary/rollback operations and safe-disable procedures.
- Add validation evidence commands and expected operator-visible outputs.

## Deliverables

- [ ] Runbook section(s) for v2 async push operations and incident handling.
- [ ] Monitoring/dashboard/alert definitions linked from docs.
- [ ] Verification commands for SSE behavior, webhook delivery success/failure, and security failures.
- [ ] KPI baseline and target report template for:
  - polling request-rate reduction,
  - SSE propagation latency,
  - webhook delivery latency and success rate.

## Acceptance Criteria

- [ ] Operators can diagnose and recover from async push delivery incidents using runbook steps alone.
- [ ] Alert thresholds cover backlog growth, retry storms, DLQ growth, and delivery latency spikes.
- [ ] Rollback and feature-disable procedures are tested and documented.
- [ ] Documentation validators pass with updated runbooks and links.
- [ ] KPI targets are explicitly testable and tracked:
  - >=60% polling request-rate reduction for push-enabled clients vs baseline,
  - SSE propagation p95 <= 2s,
  - webhook initial delivery p95 <= 5s and success >= 99% within first 3 attempts.

## Validation Evidence

- [ ] Commands/log evidence captured for SSE stream behavior.
- [ ] Commands/log evidence captured for webhook success and retry/failure paths.
- [ ] Commands/log evidence captured for invalid signature/timestamp/replay rejection paths.
- [ ] Baseline vs post-enable KPI evidence captured and linked.
- [ ] `pdm run run-local-pdm coverage-gate` output captured (`>=90%`).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
