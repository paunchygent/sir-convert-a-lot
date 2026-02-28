---
id: 'task-55-implement-v2-async-push-events-webhooks-security-and-retries'
title: 'Implement v2 async push events webhooks security and retries'
type: 'task'
status: 'proposed'
priority: 'critical'
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - implementation
  - v2
  - async-push
  - security
  - retries
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the ADR-approved v2 async push surface, including SSE streaming, webhook delivery,
security enforcement, and resilient retry behavior, while preserving polling fallback.

## PR Scope

- Implement async event emission from v2 job lifecycle transitions.
- Implement SSE stream support for live job progress/terminal events.
- Implement webhook delivery worker/path with:
  - signed payloads,
  - timestamp/replay checks,
  - retry with backoff,
  - terminal failure handling and DLQ handoff semantics.
- Implement idempotency/dedup protections for emitted events and webhook deliveries.
- Add feature flags and config gates for controlled rollout and safe disable.
- Preserve existing polling behavior and contracts.
- Update core API and internal module docs to reflect implementation semantics.

Out of scope:

- Any reintroduction or expansion of v1 API behavior.
- Removal of polling endpoints or polling-compatible client flows.

## Deliverables

- [ ] SSE endpoint and event stream behavior implemented in v2 service.
- [ ] Webhook callback delivery pipeline with retry and security validation.
- [ ] Contract/integration tests for success/failure/retry/idempotency behavior.
- [ ] Feature flag toggles and rollback-safe disable behavior.

## Acceptance Criteria

- [ ] End-to-end SSE flow verified for progress and terminal states.
- [ ] Webhook success/failure retries are deterministic and test-backed.
- [ ] Signature and replay protection checks block invalid callbacks.
- [ ] Polling fallback remains fully functional with no regression.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
