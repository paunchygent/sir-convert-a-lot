---
type: decision
id: ADR-0003
title: V2 Async Push Delivery with SSE Webhooks and Polling Fallback
status: proposed
created: '2026-02-28'
updated: '2026-02-28'
owners:
  - platform
tags:
  - adr
  - api
  - v2
  - async-push
  - sse
  - webhooks
links:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md
  - docs/converters/multi_format_conversion_service_api_v2.md
---

## Status

- Proposed
- Date: 2026-02-28

## 1. Problem and Context

The current interaction model for conversion jobs is submit + poll only. For long-running jobs
this causes avoidable issues:

- high poll frequency and elevated API load,
- delayed progress visibility for UI users,
- weaker integration ergonomics for server-to-server consumers.

Epic 05 defines a v2-only core with deterministic contracts for downstream integrations. Push
delivery is needed to make the v2 surface production-ready without removing polling compatibility.

## 2. Decision

Adopt a hybrid interaction model on v2:

- keep polling endpoints as supported fallback,
- add SSE for live UI progress consumption,
- add webhooks for server-to-server callbacks.
- add webhook onboarding APIs for endpoint/secret lifecycle management.

Push channels are additive and do not remove existing v2 polling behavior.

## 3. Scope and Versioning

- Push support is introduced on v2 only.
- No v1 expansion is allowed.
- Polling remains a supported path for clients that do not adopt push.
- Push semantics are normative through v2 contract docs and test evidence.
- SSE scope for initial release is per-job streams only; tenant/global multiplexed streams are out of
  scope for this slice.

## 4. Chosen Channels

1. SSE

- Purpose: low-latency UI progress and terminal-state updates.
- Consumption model: long-lived stream with ordered per-job events.

2. Webhooks

- Purpose: asynchronous callbacks for backend integrations.
- Consumption model: signed HTTP callbacks with retry/backoff on failure.
- Subscription model: API-managed webhook registrations with explicit ownership, status, and secret lifecycle.

3. Polling fallback

- Purpose: compatibility and recovery path.
- Consumption model: existing v2 job status/result endpoints remain valid.

## 5. Contract Rules

- Event identity:
  - each event has immutable `event_id`,
  - each event includes `job_id` and `event_type`.
- Subscription management:
  - webhook endpoints are managed through v2 onboarding APIs (`create`, `list`, `update`, `delete`),
  - each subscription has stable `subscription_id` and owner scope,
  - callback delivery for disabled/deleted subscriptions must stop deterministically.
- Ordering:
  - per-job ordering is guaranteed by monotonic `sequence`,
  - consumers must not assume cross-job global ordering.
- Idempotency and dedup:
  - `event_id` is the canonical dedup key for consumers,
  - webhook delivery attempts for the same event must keep the same `event_id`.
- Delivery semantics:
  - at-least-once delivery for webhooks,
  - SSE may reconnect and replay from a supplied cursor/event id contract.
- Replay retention contract:
  - replay horizon is 24h from event creation,
  - when cursor/event id is outside replay horizon, SSE returns `410 cursor_expired` with latest
    resumable cursor metadata,
  - replay retention is independent from artifact retention and may be shorter.
- Terminal-state behavior:
  - each job emits exactly one terminal state (`succeeded`, `failed`, or `canceled`),
  - no non-terminal event is emitted after terminal state,
  - terminal event payload includes enough data to retrieve artifacts or failure details.

## 6. Security Model

- Webhook signing:
  - HMAC signatures over timestamp + payload using shared secret.
- Replay protection:
  - include signed timestamp header,
  - enforce bounded replay window,
  - reject stale or duplicated deliveries within replay window policy.
- Secret handling:
  - secrets are system-generated and never re-readable after creation,
  - support secret rotation with overlap period (`active` + `next` secret),
  - include deterministic rotate/revoke workflows through onboarding APIs.
- Auth and rate limits:
  - v2 auth requirements remain enforced,
  - channel-specific rate limits protect stream/callback abuse paths.

## 7. Operational Model

- Delivery architecture:
  - event emission from job lifecycle transitions,
  - queue-backed webhook delivery worker,
  - bounded retries with backoff and DLQ handoff on exhaustion.
- Observability:
  - metrics for queue depth, delivery latency, retry count, DLQ growth, stream clients,
  - traces that correlate job execution to push emission and webhook delivery,
  - structured logs with job/event/delivery correlation ids.
- Alerting:
  - alert on retry storms, sustained delivery latency, DLQ threshold breach, and callback failure rates.
- Production targets:
  - push-enabled clients should reduce polling request rate by at least 60% versus baseline polling-only clients,
  - SSE event propagation p95 from job-state transition to client-visible event <= 2s,
  - webhook initial delivery p95 <= 5s and success rate >= 99% within first 3 attempts.

## 8. Rollout and Rollback

- Rollout:
  - guard SSE and webhooks behind explicit feature flags,
  - canary by internal consumers before wider enablement,
  - promote based on delivery and error-budget metrics.
- Rollback:
  - disable push channels via feature flags without breaking polling,
  - keep polling paths as immediate safe fallback,
  - preserve queued events for controlled recovery when re-enabled.

## 9. Consequences

Benefits:

- improved UX for long jobs via live updates,
- reduced poll pressure on API infrastructure,
- stronger downstream integration model for Skriptoteket, HuleEdu, and Projektveckor.

Tradeoffs:

- more infra complexity (eventing, retries, DLQ, monitoring),
- stricter operational and security requirements,
- additional contract surface requiring disciplined version governance.

This tradeoff is preferred because it materially improves production reliability and integration
ergonomics while preserving a safe polling fallback and maintaining v2-only architecture goals.
