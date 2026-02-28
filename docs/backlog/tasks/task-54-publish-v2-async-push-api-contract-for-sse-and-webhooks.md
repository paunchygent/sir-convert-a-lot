---
id: 'task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks'
title: 'Publish v2 async push API contract for SSE and webhooks'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - api-contract
  - v2
  - async-push
  - sse
  - webhooks
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish normative async push contract documentation for v2 so downstream systems can integrate SSE
and webhooks without reverse-engineering internal behavior.

## PR Scope

- Add a dedicated converter contract doc:
  - `docs/converters/multi_format_conversion_service_api_v2_async_push.md`.
- Define v2 async surfaces, including at minimum:
  - SSE stream endpoint and event framing semantics,
  - webhook callback contract and delivery semantics,
  - webhook onboarding APIs (create/list/get/update/delete),
  - webhook secret lifecycle semantics (issue/rotate/revoke),
  - polling fallback interaction model.
- Define normalized event schema and payload requirements:
  - `event_id`, `event_type`, `sequence`, `occurred_at`, `job_id`,
  - status snapshot fields,
  - route key metadata,
  - idempotency/dedup keys.
- Define delivery semantics:
  - ordering rules per job,
  - retries/backoff behavior for webhooks,
  - terminal event guarantees,
  - duplicate delivery handling requirements,
  - SSE replay retention horizon and `cursor_expired` behavior.
- Include security contract:
  - signature headers,
  - timestamp/replay policy,
  - expected auth scopes and rate limits.
- Include integration examples for Skriptoteket, HuleEdu, and Projektveckor client patterns.
- Include explicit non-goal statement: tenant/global SSE streams are out of scope for this slice.

## Deliverables

- [ ] `docs/converters/multi_format_conversion_service_api_v2_async_push.md` created and linked.
- [ ] Existing v2 converter doc updated with pointer to async push contract.
- [ ] Example request/response/event payloads published for SSE + webhook + polling fallback.
- [ ] Onboarding flow examples published (subscription create/update/rotate/delete).

## Acceptance Criteria

- [ ] Contract doc is complete enough for implementation and downstream integration.
- [ ] Contract semantics align with ADR decisions from Task 53.
- [ ] No contract text implies v1 push support or v1 expansion.
- [ ] Contract includes measurable KPI targets and replay retention constraints.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
