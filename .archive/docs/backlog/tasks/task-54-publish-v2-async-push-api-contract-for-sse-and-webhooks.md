---
id: task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks
title: Publish v2 async push API contract for SSE and webhooks
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/multi_format_conversion_service_api_v2_async_push.md
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

## Sequencing and Dependencies

1. This is `T03` in Epic 05 and may start only after `T02` Task 53 is terminal (`completed`) with
   ADR `0003` in `accepted` status.
1. Task 54 blocks implementation tasks `T13-T16` because payload/endpoint/replay/signature
   semantics must be contract-locked first.
1. Task 54 must explicitly bind to constants pinned in ADR `0003` (no re-interpretation in code).

## Deliverables

- [x] `docs/converters/multi_format_conversion_service_api_v2_async_push.md` created and linked.
- [x] Existing v2 converter doc updated with pointer to async push contract.
- [x] Example request/response/event payloads published for SSE + webhook + polling fallback.
- [x] Onboarding flow examples published (subscription create/update/rotate/delete).
- [x] Security/header canonicalization examples published (`X-SCAL-Webhook-*` headers + signature
  verification input).
- [x] Replay and retry policy examples match ADR constants (`410 cursor_expired`, retry schedule,
  DLQ criteria).

## Acceptance Criteria

- [x] Contract defines endpoint set and request/response semantics for:
  - SSE stream subscribe/replay,
  - webhook onboarding CRUD + rotate/revoke,
  - webhook callback payload + headers,
  - polling fallback interaction.
- [x] Contract semantics are identical to ADR `0003` constants (event types, replay, security,
  retry/DLQ).
- [x] No contract text implies v1 push support or v1 expansion.
- [x] Contract includes measurable KPI targets and replay retention constraints.
- [x] Contract includes deterministic error taxonomy for push surfaces (including
  `cursor_expired`, signature errors, onboarding validation errors).

## Execution Plan (Slice 54A, 2026-02-28)

1. Validate Task 53 completion and ADR acceptance state.
1. Author dedicated async contract document for v2 push surfaces.
1. Add endpoint/event schema examples for SSE, onboarding, webhook deliveries, and polling fallback.
1. Add explicit downstream integration examples for Skriptoteket, HuleEdu, and Projektveckor.
1. Cross-link from existing converter docs and run docs validators.

## Risk Controls

- Ambiguous contract risk:
  - every normative behavior must include concrete payload/headers/status examples.
- Drift risk:
  - contract constants must reference ADR and be grep-checkable.
- Legacy regression risk:
  - include explicit v2-only/no-v1 statement in async contract.

## Test Matrix (Minimum)

- Contract completeness checks:
  - all required endpoint families documented with examples.
- Determinism checks:
  - event/replay/signature/retry constants match ADR text exactly.
- Traceability checks:
  - links to Story 15 and Tasks 55/56/57/58 exist.

## Validation Commands

- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- `rg -n "event_id|event_type|sequence|occurred_at|cursor_expired|X-SCAL-Webhook|retry|DLQ|polling fallback" docs/converters/multi_format_conversion_service_api_v2_async_push.md`
- `rg -n "multi_format_conversion_service_api_v2_async_push\\.md" docs/converters/multi_format_conversion_service_api_v2.md`
- `rg -n "Update request example|Rotate-secret request example|Delete response semantics" docs/converters/multi_format_conversion_service_api_v2_async_push.md`
- `rg -n "webhook_signature_invalid|webhook_timestamp_outside_window|webhook_replay_detected" docs/converters/multi_format_conversion_service_api_v2_async_push.md`
- `rg -n "Authorization requirements|jobs:read|push:read|push:write|rate_limited|Retry-After|429 Too Many Requests" docs/converters/multi_format_conversion_service_api_v2_async_push.md`

## Execution Outcome

- [x] Async push contract doc published and linked.
- [x] Contract validated against ADR constants and Story 15 acceptance mapping.

### Validation Evidence

- [x] Validation command outputs captured.
- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
- `rg -n "event_id|event_type|sequence|occurred_at|cursor_expired|X-SCAL-Webhook|retry|DLQ|polling fallback" docs/converters/multi_format_conversion_service_api_v2_async_push.md` (pass)
- `rg -n "multi_format_conversion_service_api_v2_async_push\\.md" docs/converters/multi_format_conversion_service_api_v2.md` (pass)
- `rg -n "Update request example|Rotate-secret request example|Delete response semantics" docs/converters/multi_format_conversion_service_api_v2_async_push.md` (pass)
- `rg -n "webhook_signature_invalid|webhook_timestamp_outside_window|webhook_replay_detected" docs/converters/multi_format_conversion_service_api_v2_async_push.md` (pass)
- `rg -n "Authorization requirements|jobs:read|push:read|push:write|rate_limited|Retry-After|429 Too Many Requests" docs/converters/multi_format_conversion_service_api_v2_async_push.md` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
