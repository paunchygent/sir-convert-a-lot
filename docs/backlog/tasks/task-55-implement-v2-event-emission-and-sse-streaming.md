---
id: 'task-55-implement-v2-event-emission-and-sse-streaming'
title: 'Implement v2 event emission and SSE streaming'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - implementation
  - v2
  - async-push
  - sse
  - events
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement v2 job-event emission and SSE streaming (including replay cursor behavior) while keeping
polling fallback unchanged.

## PR Scope

- Implement async event emission from v2 job lifecycle transitions.
- Implement SSE stream support for live job progress/terminal events.
- Implement SSE replay semantics:
  - cursor/event-id resume,
  - `410 cursor_expired` for stale cursors outside replay horizon.
- Implement idempotency/dedup protections for emitted SSE events.
- Add SSE-specific feature flag/config gate for controlled rollout and safe disable.
- Preserve existing polling behavior and contracts.
- Update core API and internal module docs to reflect implementation semantics.

Out of scope:

- Webhook subscription onboarding APIs and secret lifecycle (Task 57).
- Webhook delivery worker, signing, retries, and replay protection enforcement (Task 58).

## Deliverables

- [ ] SSE endpoint and event stream behavior implemented in v2 service.
- [ ] Event emission model with per-job sequence and event ids.
- [ ] Contract/integration tests for SSE progress/terminal/replay/idempotency behavior.
- [ ] Feature flag toggles and rollback-safe disable behavior for SSE lane.

## Acceptance Criteria

- [ ] End-to-end SSE flow verified for progress and terminal states.
- [ ] Stale cursor replay attempts return deterministic `410 cursor_expired`.
- [ ] Polling fallback remains fully functional with no regression.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
