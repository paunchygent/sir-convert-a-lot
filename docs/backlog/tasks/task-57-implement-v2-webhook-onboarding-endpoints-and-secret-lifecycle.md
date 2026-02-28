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

## Sequencing and Dependencies

1. This is `T14` in Epic 05.
1. Task 57 depends on:
   - `T02` Task 53 (ADR accepted),
   - `T03` Task 54 (webhook onboarding contract published).
1. Task 57 should complete before Task 58 so delivery worker logic targets finalized subscription
   and secret lifecycle models.

## Deliverables

- [ ] V2 webhook onboarding endpoints implemented and wired to auth/ownership model.
- [ ] Secret lifecycle actions (`create`, `rotate`, `revoke`) implemented.
- [ ] Contract tests for CRUD + secret lifecycle + authorization + validation failures.
- [ ] Overlap-window behavior for secret rotation implemented with deterministic timing semantics.

## Acceptance Criteria

- [ ] Downstream consumers can configure and manage callbacks without infra-side static config.
- [ ] Secret values are never leaked in read/list responses after creation/rotation.
- [ ] Subscription disable/delete deterministically stops future callback deliveries.
- [ ] API contract docs match implemented onboarding behavior.

## Execution Plan (Slice 57A, 2026-02-28)

1. Implement subscription persistence model (`create/list/get/update/delete`).
1. Implement owner-scoped authorization and endpoint/status validation.
1. Implement secret create/rotate/revoke flow with fixed overlap-window behavior.
1. Ensure read/list responses redact secret material deterministically.
1. Add contract tests for CRUD/auth/validation/rotation overlap/revocation semantics.

## Risk Controls

- Secret leakage risk:
  - assert no secret values in read/list logs and response payloads.
- Ownership bypass risk:
  - add negative tests for cross-owner access and mutation attempts.
- Delivery coupling risk:
  - verify disable/delete flags are consumed by enqueue path contracts (Task 58 dependency).

## Test Matrix (Minimum)

- Onboarding CRUD:
  - create/list/get/update/delete success paths.
- Security/ownership:
  - unauthorized and cross-owner access failures.
- Secret lifecycle:
  - create-only visibility,
  - rotate overlap window behavior,
  - revoke behavior.
- Integration guard:
  - disable/delete subscriptions are not eligible for enqueue.

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

- [ ] CRUD/auth/secret-lifecycle test outputs captured.
- [ ] Coverage gate output captured (`>=90%`).
- [ ] Docs/task validators and index output captured.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
