---
id: task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection
title: Implement v2 webhook delivery worker retries signatures and replay protection
type: task
status: proposed
priority: critical
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - implementation
  - v2
  - webhooks
  - retries
  - security
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement resilient webhook delivery for v2 push events with signing, replay protection, and
deterministic retry/DLQ behavior.

## PR Scope

- Implement queue-backed webhook delivery worker for subscribed callbacks.
- Implement webhook signing and validation contract support:
  - HMAC signature headers,
  - signed timestamp,
  - deterministic canonical payload input.
- Implement retry/backoff behavior with attempt limits and DLQ handoff.
- Implement replay protection semantics and duplicate-delivery safety guarantees.
- Implement feature flags for webhook lane enable/disable and safe rollback.
- Add delivery observability hooks (attempt counts, latency, failure reason classes).

## Sequencing and Dependencies

1. This is `T15` in Epic 05.
1. Task 58 depends on:
   - `T02` Task 53 (security/retry constants accepted),
   - `T03` Task 54 (normative async contract),
   - `T13` Task 55 (shared event model),
   - `T14` Task 57 (subscription + secret lifecycle model).
1. Task 58 must finish before Task 56 operational sign-off.

## Internal Slice Decomposition

1. `58A` delivery reliability core:
   - queue consumer,
   - retry/backoff attempts,
   - DLQ handoff and metadata.
1. `58B` security + rollback + KPI instrumentation:
   - signature/timestamp/replay enforcement,
   - feature-flag safe disable,
   - latency/success instrumentation used by Task 56 KPI report.

## Deliverables

- [ ] Webhook delivery worker implemented with retry/backoff + DLQ integration.
- [ ] Signature/timestamp/replay protection enforcement implemented and documented.
- [ ] Integration tests for success path, retry path, DLQ path, and security failure path.
- [ ] Adapter non-GPU E2E conformance test updated in the same PR immediately after webhook push-logic changes (`tests/sir_convert_a_lot/test_integration_adapter_conformance.py::test_adapter_integration_smoke_submit_poll_fetch_without_gpu_runtime`).
- [ ] Feature-flagged rollback-safe disable behavior for webhook lane.
- [ ] `58A` and `58B` sub-slices both completed with separate evidence capture.

## Acceptance Criteria

- [ ] Webhook callback success/failure behavior is deterministic and test-backed.
- [ ] Invalid signature, stale timestamp, and replay attempts are rejected predictably.
- [ ] DLQ receives exhausted deliveries with actionable failure metadata.
- [ ] Webhook delivery meets Story 15 performance/reliability targets.

## Execution Plan (Slice 58A/58B, 2026-02-28)

1. Implement queue consumer and deterministic delivery-attempt model (`58A`).
1. Implement retry schedule + max-attempt logic and DLQ handoff (`58A`).
1. Add delivery integration tests for success/retry/DLQ outcomes (`58A`).
1. Implement signature header verification and replay-window enforcement (`58B`).
1. Implement feature-flag safe disable and no-op behavior for webhook lane (`58B`).
1. Add security negative tests and KPI instrumentation fields (`58B`).
1. Update adapter non-GPU E2E test in the same PR immediately after webhook push-logic changes.

## Risk Controls

- Retry storm risk:
  - cap attempts and enforce backoff schedule from ADR.
- DLQ blind-spot risk:
  - include failure reason class + attempt metadata in DLQ payload.
- Signature drift risk:
  - enforce canonical header names and signing input exactly as ADR.
- Rollback risk:
  - feature flags must disable delivery without affecting polling/SSE behavior.

## Test Matrix (Minimum)

- `58A` reliability tests:
  - first-attempt success,
  - retry progression,
  - attempt exhaustion to DLQ,
  - deterministic idempotent event delivery metadata.
- `58B` security tests:
  - invalid signature rejection,
  - stale timestamp rejection,
  - replay attempt rejection.
- Integration regression:
  - polling fallback unchanged,
  - adapter non-GPU E2E path updated and passing.

## Validation Commands

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Validation Evidence

- [ ] `58A` success/retry/DLQ test outputs captured.
- [ ] `58B` signature/replay/timestamp rejection test outputs captured.
- [ ] Adapter non-GPU E2E update evidence captured.
- [ ] Coverage gate output captured (`>=90%`).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
