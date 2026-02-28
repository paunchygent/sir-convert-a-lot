---
id: 'story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback'
title: 'V2 async push channels SSE webhooks and polling fallback'
type: 'story'
status: 'proposed'
priority: 'critical'
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-55-implement-v2-async-push-events-webhooks-security-and-retries.md
  - docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - v2
  - async-push
  - sse
  - webhooks
  - polling-fallback
---
Implementation slice with acceptance-driven scope.

## Objective

Add production-ready async push channels to the v2 conversion API while preserving polling as a
supported fallback, so long-running jobs can be consumed with lower latency and less client-side
poll churn.

## Scope

- Deliver an ADR-backed hybrid model for v2 only:
  - SSE for live UI progress updates,
  - webhooks for server-to-server callback delivery,
  - polling preserved as fallback.
- Define and publish normative async push contracts (events, payload schemas, ordering,
  idempotency, retries, and terminal-state semantics).
- Implement push emission, delivery worker behavior, webhook security (HMAC + replay protection),
  and operational controls (feature flags/canary/rollback).
- Publish operating guidance and observability expectations for push delivery reliability.
- Sequence this story after core clean-break hardening to avoid contract churn:
  - Story 14 v2-only API unification.
  - Story 12 legacy/eval path cleanup.

Out of scope:

- Any restoration or extension of v1 conversion surfaces.
- Removal of polling behavior.

## Acceptance Criteria

- [ ] ADR is approved and linked from story/tasks.
- [ ] V2 async push contract doc is normative and complete for SSE + webhooks + polling fallback.
- [ ] Push implementation provides deterministic event semantics (ordering/idempotency/terminal behavior).
- [ ] Webhook security controls are implemented and validated (signature, timestamp, replay window).
- [ ] Rollout/rollback controls are documented and verified for safe disable.

## Test Requirements

- [ ] End-to-end SSE stream verification for active + terminal job states.
- [ ] Webhook success/failure retry behavior and terminal-state callback behavior are proven.
- [ ] Negative security tests cover signature mismatch, stale timestamp, and replay attempts.
- [ ] Polling fallback remains functional and unchanged for clients that do not adopt push.

## Done Definition

V2 supports production-grade async push channels with preserved polling fallback, and the full
contract/ops surface is documented and test-backed for downstream integrations.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
