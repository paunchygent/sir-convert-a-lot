---
id: task-55-implement-v2-event-emission-and-sse-streaming
title: Implement v2 event emission and SSE streaming
type: task
status: completed
priority: high
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

## Sequencing and Dependencies

1. This is `T13` in Epic 05.
1. Task 55 depends on:
   - `T02` Task 53 (ADR accepted with constants),
   - `T03` Task 54 (normative async contract published).
1. Task 55 must complete before Task 58 delivery-worker implementation because webhook delivery
   consumes the shared event model.

## Deliverables

- [x] SSE endpoint and event stream behavior implemented in v2 service.
- [x] Event emission model with per-job sequence and event ids.
- [x] Contract/integration tests for SSE progress/terminal/replay/idempotency behavior.
- [x] Adapter non-GPU E2E conformance test updated in the same PR immediately after SSE push-logic changes (`tests/sir_convert_a_lot/test_integration_adapter_conformance.py::test_adapter_integration_smoke_submit_poll_fetch_without_gpu_runtime`).
- [x] Feature flag toggles and rollback-safe disable behavior for SSE lane.
- [x] KPI instrumentation fields emitted for SSE latency measurement (needed by Task 56 KPI sign-off).

## Acceptance Criteria

- [x] End-to-end SSE flow verified for progress and terminal states.
- [x] Stale cursor replay attempts return deterministic `410 cursor_expired`.
- [x] Polling fallback remains fully functional with no regression.
- [x] Event ordering and dedup are deterministic per job (`sequence` monotonic, stable `event_id`).

## Execution Plan (Slice 55A, 2026-02-28)

1. Implement shared event model and persistence for per-job ordered events.
1. Implement SSE subscribe endpoint with resume-from-cursor/event-id support.
1. Implement cursor expiry handling with deterministic `410 cursor_expired`.
1. Add feature flag guard and rollback-safe disable behavior.
1. Add targeted SSE integration tests plus polling regression tests.
1. Update adapter non-GPU E2E test in the same PR immediately after push-logic changes.

## Risk Controls

- Polling regression risk:
  - keep existing poll endpoints untouched and add explicit regression tests.
- Replay correctness risk:
  - test stale cursor, missing cursor, and exact replay boundary behavior.
- Throughput risk:
  - emit lightweight event payloads and instrument p95 latency metrics for Task 56 validation.

## Test Matrix (Minimum)

- `tests/sir_convert_a_lot/test_api_contract_v2.py` (polling fallback regression)
- `tests/sir_convert_a_lot/test_integration_adapter_conformance.py::test_adapter_integration_smoke_submit_poll_fetch_without_gpu_runtime` (updated in same PR)
- New/updated SSE tests:
  - stream progress + terminal events,
  - cursor resume replay,
  - stale cursor `410 cursor_expired`,
  - dedup/ordering assertions.

## Validation Commands

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_sse.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Validation Evidence

- [x] Targeted SSE + polling regression command outputs captured.
- [x] Adapter non-GPU E2E update evidence captured.
- [x] Coverage gate output captured (`>=90%`).
- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 145 source files`)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_sse.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py` (pass: `22 passed, 3 skipped`)
- `pdm run run-local-pdm coverage-gate` (pass: `352 passed, 5 skipped`; total coverage `94.76%`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=105 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
