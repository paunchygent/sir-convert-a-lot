---
id: 'task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback'
title: 'ADR v2 async push delivery model SSE webhooks polling fallback'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
labels:
  - adr
  - v2
  - async-push
  - architecture
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish a decision record that defines the production async push model for v2 conversion jobs.

## PR Scope

- Document problem context: submit + poll only creates avoidable load, latency, and UX degradation.
- Decide on hybrid model:
  - keep polling as fallback,
  - add SSE for UI/live progress,
  - add webhooks for server-to-server callbacks.
- Define scope/versioning as v2-only push capabilities (no v1 expansion).
- Define contract rules:
  - event types,
  - ordering guarantees,
  - idempotency semantics,
  - delivery/retry behavior,
  - terminal-state behavior.
- Define security model:
  - HMAC signatures,
  - timestamp + replay window,
  - secret rotation posture,
  - auth/rate-limits.
- Define operational model:
  - queueing,
  - retry/DLQ policy,
  - observability + alert thresholds.
- Define rollout/rollback strategy with feature flags and canary sequencing.
- Record tradeoffs and consequences.

## Deliverables

- [ ] ADR document created at `docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md`.
- [ ] ADR links to Story 15 and tasks 54-58.
- [ ] ADR includes explicit v2-only push scope and polling fallback invariants.

## Acceptance Criteria

- [ ] ADR provides implementation-grade guidance for API, security, operations, and rollout.
- [ ] ADR does not introduce any v1 compatibility requirement.
- [ ] ADR is referenced by async contract docs and implementation task(s).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
