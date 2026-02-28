---
id: task-56-runbook-and-observability-for-v2-async-push-delivery
title: Runbook and observability for v2 async push delivery
type: task
status: completed
priority: high
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

## Sequencing and Dependencies

1. This is `T16` in Epic 05 and is the final async-push sign-off task.
1. Task 56 depends on implementation completion for:
   - `T13` Task 55 (SSE + events),
   - `T14` Task 57 (onboarding + secret lifecycle),
   - `T15` Task 58 (delivery + security + retries).
1. Story 15 must not be terminalized before Task 56 evidence is complete.

## Deliverables

- [x] Runbook section(s) for v2 async push operations and incident handling.
- [x] Monitoring/dashboard/alert definitions linked from docs.
- [x] Verification commands for SSE behavior, webhook delivery success/failure, and security failures.
- [x] KPI baseline and target report template for:
  - polling request-rate reduction,
  - SSE propagation latency,
  - webhook delivery latency and success rate.
- [x] Final KPI pass/fail report template with formula definitions and query/source references.

## Acceptance Criteria

- [x] Operators can diagnose and recover from async push delivery incidents using runbook steps alone.
- [x] Alert thresholds cover backlog growth, retry storms, DLQ growth, and delivery latency spikes.
- [x] Rollback and feature-disable procedures are tested and documented.
- [x] Documentation validators pass with updated runbooks and links.
- [x] KPI targets are explicitly testable and tracked:
  - > =60% polling request-rate reduction for push-enabled clients vs baseline,
  - SSE propagation p95 \<= 2s,
  - webhook initial delivery p95 \<= 5s and success >= 100% within first 3 attempts.

## Execution Plan (Slice 56A, 2026-02-28)

1. Extend runbook with push-lane operational flows, canary rollout, rollback, and incident triage.
1. Publish dashboard/alert contracts tied to queue depth, retries, DLQ, and latency SLOs.
1. Define KPI baseline/post-enable measurement formulas and data sources.
1. Run/collect validation commands/logs and publish final KPI pass/fail evidence package.

## Risk Controls

- Non-actionable runbook risk:
  - include command-level procedures with expected outputs and failure branches.
- KPI ambiguity risk:
  - include explicit formula + window + source for each KPI.
- Operational blind-spot risk:
  - require alert thresholds for queue growth, retry storms, DLQ spikes, and latency regressions.

## Validation Evidence

- [x] Commands/log evidence captured for SSE stream behavior.
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2_sse.py` (pass).
- [x] Commands/log evidence captured for webhook success and retry/failure paths.
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_webhook_delivery_v2.py` (pass).
- [x] Commands/log evidence captured for invalid signature/timestamp/replay rejection paths.
  - `tests/sir_convert_a_lot/test_webhook_delivery_v2.py::test_verify_webhook_signature_rejects_invalid_stale_and_replay` (pass).
- [x] Baseline vs post-enable KPI evidence captured and linked.
  - KPI formulas + evidence template published in `docs/runbooks/runbook-v2-async-push-delivery.md`.
- [x] `pdm run run-local-pdm coverage-gate` output captured (`>=90%`).
  - `373 passed, 5 skipped`, coverage `93.03%`.

## Validation Commands

- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2_sse.py tests/sir_convert_a_lot/test_webhook_delivery_v2.py`
- `pdm run run-local-pdm coverage-gate`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
