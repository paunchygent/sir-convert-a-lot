---
id: task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle
title: Implement v2 webhook onboarding endpoints and secret lifecycle
type: task
status: proposed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - implementation
  - v2
  - webhooks
  - onboarding
  - security
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement v2 webhook subscription onboarding APIs so downstream consumers can self-manage callback
endpoints and secrets safely.

## PR Scope

- Add onboarding API surfaces for webhook subscriptions:
  - create,
  - list/get,
  - update (endpoint/status/event filter),
  - delete/disable.
- Add deterministic secret lifecycle semantics:
  - secret issued at create time and never re-readable,
  - rotate secret operation with overlap window,
  - revoke/deactivate behavior.
- Enforce owner-scoped access control for subscription operations.
- Add validation and deterministic error mapping for malformed URLs, invalid ownership, and
  duplicate endpoint constraints.
- Update contract docs and examples for onboarding flows.

## Deliverables

- [ ] V2 webhook onboarding endpoints implemented and wired to auth/ownership model.
- [ ] Secret lifecycle actions (`create`, `rotate`, `revoke`) implemented.
- [ ] Contract tests for CRUD + secret lifecycle + authorization + validation failures.

## Acceptance Criteria

- [ ] Downstream consumers can configure and manage callbacks without infra-side static config.
- [ ] Secret values are never leaked in read/list responses after creation/rotation.
- [ ] Subscription disable/delete deterministically stops future callback deliveries.
- [ ] API contract docs match implemented onboarding behavior.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
