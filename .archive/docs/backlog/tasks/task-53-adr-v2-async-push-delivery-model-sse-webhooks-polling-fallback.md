---
id: task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback
title: ADR v2 async push delivery model SSE webhooks polling fallback
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md
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

Finalize and accept the decision record that defines the production async push model for v2
conversion jobs.

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
- Resolve and pin implementation constants required for deterministic contract/tests:
  - canonical event-type set,
  - replay horizon and cursor expiry behavior,
  - webhook signature headers/canonicalization,
  - replay window duration,
  - retry schedule + max attempts + DLQ handoff thresholds.

## Sequencing and Dependencies

1. This is `T02` in Epic 05 and must complete before `T03` Task 54 begins.
1. Task 53 blocks all push implementation tasks (`T13-T16`) because ADR constants govern
   contract, test, and operational behavior.
1. Task 53 terminalization requires ADR status transition from `proposed` to `accepted`.

## Deliverables

- [x] ADR document finalized at `docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md`.
- [x] ADR status transitioned to `accepted`.
- [x] ADR links to Story 15 and tasks 54-58.
- [x] ADR includes explicit v2-only push scope and polling fallback invariants.
- [x] ADR pins deterministic policy constants for security, replay, retry, and DLQ behavior.

## Acceptance Criteria

- [x] ADR provides implementation-grade guidance for API, security, operations, and rollout.
- [x] ADR does not introduce any v1 compatibility requirement.
- [x] ADR constants are sufficiently specific for Task 54 contract publication and Tasks 55/57/58
  implementation without additional policy decisions.
- [x] ADR is referenced by async contract docs and implementation task(s).

## Execution Plan (Slice 53A, 2026-02-28)

1. Review Story 15 acceptance criteria and map them to explicit ADR decision bullets.
1. Finalize unresolved policy constants in ADR section 5-7 (event, replay, security, retry/DLQ).
1. Ensure links and traceability across Story 15 and Tasks 54-58 are complete.
1. Move ADR status to `accepted` and record acceptance date.
1. Run docs-as-code validation and grep checks for required constants.

## Risk Controls

- Under-specified policy risk:
  - reject vague language; constants must be numeric/testable.
- Contract drift risk:
  - ensure Task 54 references the exact ADR constants.
- Reintroduction risk:
  - keep v2-only scope and explicit no-v1-expansion statements.

## Test Matrix (Minimum)

- Decision consistency checks:
  - Story 15 acceptance criteria can be mapped directly to ADR clauses.
- Determinism checks:
  - replay/security/retry constants are explicit and non-ambiguous.
- Traceability checks:
  - ADR cross-links cover Tasks 54-58 and Story 15.

## Validation Commands

- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- `rg -n "status: accepted|task-54|task-55|task-56|task-57|task-58|story-15" docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md`
- `rg -n "event_id|event_type|sequence|cursor_expired|HMAC|retry|DLQ|replay window" docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md`

## Execution Outcome

- [x] ADR finalized and accepted.
- [x] Constants pinned and validated against Story 15/Task 54 requirements.

### Validation Evidence

- [x] Validation command outputs captured.
- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
- `rg -n "status: accepted|task-54|task-55|task-56|task-57|task-58|story-15" docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md` (pass)
- `rg -n "event_id|event_type|sequence|cursor_expired|HMAC|retry|DLQ|replay window" docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
