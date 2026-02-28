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

## Deliverables

- [ ] Webhook delivery worker implemented with retry/backoff + DLQ integration.
- [ ] Signature/timestamp/replay protection enforcement implemented and documented.
- [ ] Integration tests for success path, retry path, DLQ path, and security failure path.
- [ ] Adapter non-GPU E2E conformance test updated in the same PR immediately after webhook push-logic changes (`tests/sir_convert_a_lot/test_integration_adapter_conformance.py::test_adapter_integration_smoke_submit_poll_fetch_without_gpu_runtime`).
- [ ] Feature-flagged rollback-safe disable behavior for webhook lane.

## Acceptance Criteria

- [ ] Webhook callback success/failure behavior is deterministic and test-backed.
- [ ] Invalid signature, stale timestamp, and replay attempts are rejected predictably.
- [ ] DLQ receives exhausted deliveries with actionable failure metadata.
- [ ] Webhook delivery meets Story 15 performance/reliability targets.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
