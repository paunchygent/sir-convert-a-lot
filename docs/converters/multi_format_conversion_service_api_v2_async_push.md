---
type: converter
id: CONV-multi-format-conversion-service-api-v2-async-push
title: Multi-format Conversion Service API v2 Async Push Contract
status: active
created: 2026-02-28
updated: 2026-03-04
owners:
  - platform
tags:
  - api
  - contract
  - v2
  - async-push
  - sse
  - webhooks
links:
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
---

## Purpose

Define the normative async push contract for service API v2 job lifecycles:

- SSE for UI/live progress consumption,
- webhooks for server-to-server callbacks,
- polling fallback for compatibility and recovery.

This contract is additive to the base v2 conversion contract and does not alter conversion route
semantics.

## Authority and Scope

- Base conversion contract authority:
  - `docs/converters/multi_format_conversion_service_api_v2.md`
- Decision authority:
  - `docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md`
- Downstream integration guidance:
  - `docs/converters/downstream_integration_contract_v2.md`

Version policy:

- Push support is v2-only.
- No v1 push surface is defined or supported.
- Polling remains supported and unchanged.

Non-goals for this slice:

- tenant/global multiplexed SSE streams,
- push support on v1 routes.

## Shared Event Model

Canonical event types:

- `job.queued`
- `job.running`
- `job.succeeded`
- `job.failed`
- `job.canceled`

Canonical event payload:

```json
{
  "api_version": "v2",
  "event_id": "01J7Y3T9F7Q5M7A5KQW4B9V4YQ",
  "event_type": "job.running",
  "sequence": 2,
  "occurred_at": "2026-02-28T20:45:11Z",
  "job_id": "jobv2_01J7Y3T7X6D5J2M1Q5R0T4N6P7",
  "status": "running",
  "route": {
    "source_format": "pdf",
    "target_format": "md"
  },
  "progress": {
    "stage": "convert",
    "last_heartbeat_at": "2026-02-28T20:45:10Z",
    "total_pages": 120,
    "processed_pages": 12,
    "failed_pages": 0,
    "percent_complete": 10.0,
    "pages_per_minute": 180.0,
    "eta_seconds": 360
  }
}
```

Notes:

- The page progress fields in `progress` are PDF-only per ADR-0005 and may be `null` (or omitted) for
  non-PDF routes.

Invariants:

- `event_id` is immutable and unique.
- `sequence` is monotonic per job, starts at `1`, and increments by `1`.
- Exactly one terminal event is emitted per job (`succeeded|failed|canceled`).
- No non-terminal event is emitted after terminal event.

## SSE Contract

Endpoint:

- `GET /v2/convert/jobs/{job_id}/events/stream`

Headers:

- `X-API-Key` (required)
- `X-Correlation-ID` (optional)
- `Accept: text/event-stream` (recommended)

Authorization requirements:

- API key must be valid for v2 (`auth_invalid_api_key` on failure).
- SSE stream access requires `jobs:read` capability for the owning API key.
- Job ownership is enforced; callers cannot stream events for jobs outside their API-key scope.

Rate limits:

- max concurrent SSE streams per API key: `5`
- max new SSE stream connections per API key per 60 seconds: `30`
- on limit breach, service returns:
  - `429 Too Many Requests`
  - `error.code = "rate_limited"`
  - `Retry-After: <seconds>`
  - `error.details.surface = "sse_stream"`

Query parameters:

- `cursor` (optional opaque replay cursor)
- `last_event_id` (optional event id resume pointer)

Response behavior:

- `200` opens event stream (`text/event-stream`)
- `404` when job does not exist
- `410` `cursor_expired` when replay pointer is outside replay horizon

Replay retention policy:

- replay horizon is `24h` from event creation,
- stale cursor/event-id returns `410 cursor_expired`.

SSE frame example:

```text
id: 01J7Y3T9F7Q5M7A5KQW4B9V4YQ
event: job.running
data: {"api_version":"v2","event_id":"01J7Y3T9F7Q5M7A5KQW4B9V4YQ","event_type":"job.running","sequence":2,"occurred_at":"2026-02-28T20:45:11Z","job_id":"jobv2_01J7Y3T7X6D5J2M1Q5R0T4N6P7","status":"running","route":{"source_format":"pdf","target_format":"md"},"progress":{"stage":"convert","last_heartbeat_at":"2026-02-28T20:45:10Z","total_pages":120,"processed_pages":12,"failed_pages":0,"percent_complete":10.0,"pages_per_minute":180.0,"eta_seconds":360}}
```

Cursor-expired example (`410`):

```json
{
  "api_version": "v2",
  "error": {
    "code": "cursor_expired",
    "message": "Replay cursor is outside the retention horizon.",
    "retryable": false,
    "details": {
      "replay_horizon_hours": 24
    },
    "correlation_id": "corr_..."
  }
}
```

## Webhook Onboarding Contract

Base resource:

- `/v2/push/webhooks/subscriptions`

Endpoints:

- `POST /v2/push/webhooks/subscriptions` (create)
- `GET /v2/push/webhooks/subscriptions` (list)
- `GET /v2/push/webhooks/subscriptions/{subscription_id}` (read)
- `PATCH /v2/push/webhooks/subscriptions/{subscription_id}` (update endpoint/status/event filters)
- `POST /v2/push/webhooks/subscriptions/{subscription_id}/rotate-secret` (rotate with overlap)
- `POST /v2/push/webhooks/subscriptions/{subscription_id}/revoke-secret` (revoke next/active secret)
- `DELETE /v2/push/webhooks/subscriptions/{subscription_id}` (delete)

Authorization requirements:

- API key must be valid for v2 (`auth_invalid_api_key` on failure).
- Read endpoints require `push:read` capability.
- Create/update/rotate/revoke/delete endpoints require `push:write` capability.
- Subscription ownership is enforced by API key scope.

Rate limits:

- read endpoints (`GET` list/read): `120` requests per 60 seconds per API key.
- mutating endpoints (`POST`/`PATCH`/`DELETE`): `30` requests per 60 seconds per API key.
- on limit breach, service returns:
  - `429 Too Many Requests`
  - `error.code = "rate_limited"`
  - `Retry-After: <seconds>`
  - `error.details.surface = "webhook_onboarding"`

Create request example:

```json
{
  "callback_url": "https://consumer.example/hooks/sir-convert-a-lot",
  "event_types": ["job.succeeded", "job.failed", "job.canceled"],
  "enabled": true
}
```

Create response example (`201`):

```json
{
  "api_version": "v2",
  "subscription": {
    "subscription_id": "whsub_01J7Y4D9XJ1N31A8QKR2PE5HVS",
    "callback_url": "https://consumer.example/hooks/sir-convert-a-lot",
    "event_types": ["job.succeeded", "job.failed", "job.canceled"],
    "enabled": true,
    "created_at": "2026-02-28T21:02:00Z",
    "updated_at": "2026-02-28T21:02:00Z"
  },
  "secret": {
    "version": "active",
    "value": "whsec_live_...",
    "revealed_once": true
  }
}
```

Update request example (`PATCH /v2/push/webhooks/subscriptions/{subscription_id}`):

```json
{
  "callback_url": "https://consumer.example/hooks/scal-prod",
  "event_types": ["job.succeeded", "job.failed", "job.canceled"],
  "enabled": true
}
```

Update response example (`200`):

```json
{
  "api_version": "v2",
  "subscription": {
    "subscription_id": "whsub_01J7Y4D9XJ1N31A8QKR2PE5HVS",
    "callback_url": "https://consumer.example/hooks/scal-prod",
    "event_types": ["job.succeeded", "job.failed", "job.canceled"],
    "enabled": true,
    "created_at": "2026-02-28T21:02:00Z",
    "updated_at": "2026-02-28T21:20:00Z"
  }
}
```

Rotate-secret request example (`POST /v2/push/webhooks/subscriptions/{subscription_id}/rotate-secret`):

```json
{
  "reason": "scheduled_rotation"
}
```

Rotate-secret response example (`200`):

```json
{
  "api_version": "v2",
  "subscription_id": "whsub_01J7Y4D9XJ1N31A8QKR2PE5HVS",
  "secret": {
    "version": "next",
    "value": "whsec_live_next_...",
    "revealed_once": true
  },
  "overlap": {
    "active_and_next_valid": true,
    "overlap_expires_at": "2026-03-01T21:20:00Z",
    "overlap_hours": 24
  }
}
```

Delete response semantics (`DELETE /v2/push/webhooks/subscriptions/{subscription_id}`):

- `204 No Content` on successful deletion.
- `404 webhook_subscription_not_found` if subscription id does not exist.

Secret lifecycle rules:

- secret is revealed only at create/rotate operation response,
- read/list responses must not include secret values,
- rotation overlap window is `24h`.

## Webhook Delivery Contract

Callback request method:

- `POST {callback_url}`

Required headers:

- `X-SCAL-Webhook-Id` = `event_id`
- `X-SCAL-Webhook-Timestamp` = unix-seconds
- `X-SCAL-Webhook-Signature` = `v1=<hex-hmac-sha256>`
- `Content-Type: application/json`

Canonical signing input:

- `<timestamp>.<raw-body-bytes>`

Retry/DLQ policy:

- at-least-once delivery,
- max attempts: `5` (initial + `4` retries),
- retry delays: `2s`, `10s`, `30s`, `120s`,
- exhausted deliveries move to DLQ with failure metadata.

Success and retry semantics:

- `2xx` response: delivery acknowledged, no retry.
- non-`2xx` or network timeout: retry schedule applies.

Webhook payload example:

```json
{
  "api_version": "v2",
  "event_id": "01J7Y5A8Q1F6R9V4H3T2M8D7XZ",
  "event_type": "job.succeeded",
  "sequence": 4,
  "occurred_at": "2026-02-28T21:14:10Z",
  "job_id": "jobv2_01J7Y5A5JKRN6B5N8EM2QW1G7A",
  "status": "succeeded",
  "route": {
    "source_format": "pdf",
    "target_format": "md"
  },
  "progress": {
    "stage": "succeeded",
    "last_heartbeat_at": "2026-02-28T21:14:10Z",
    "total_pages": 120,
    "processed_pages": 120,
    "failed_pages": 0,
    "percent_complete": 100.0,
    "pages_per_minute": 180.0,
    "eta_seconds": 0
  },
  "result_links": {
    "result": "/v2/convert/jobs/jobv2_01J7Y5A5JKRN6B5N8EM2QW1G7A/result",
    "artifact": "/v2/convert/jobs/jobv2_01J7Y5A5JKRN6B5N8EM2QW1G7A/artifact"
  }
}
```

## Polling Fallback Contract

Polling endpoints remain unchanged:

- `GET /v2/convert/jobs/{job_id}`
- `GET /v2/convert/jobs/{job_id}/result`
- `GET /v2/convert/jobs/{job_id}/artifact`

Push-enabled clients must still support polling fallback for:

- temporary stream disconnects,
- webhook delivery outages,
- controlled push feature-disable rollback.

Authorization requirements:

- Polling fallback keeps base v2 auth and ownership rules from
  `docs/converters/multi_format_conversion_service_api_v2.md`.
- Polling endpoints require `jobs:read` capability for the owning API key.

## Error Taxonomy (Push Surfaces)

Expected deterministic push-related codes:

- `cursor_expired` (`410`) for stale replay pointer
- `webhook_subscription_not_found` (`404`)
- `webhook_endpoint_invalid` (`422`)
- `webhook_subscription_conflict` (`409`)
- `webhook_signature_invalid` (`401`) for callback signature verification failures
- `webhook_timestamp_outside_window` (`401`) for callback timestamp outside replay window
- `webhook_replay_detected` (`409`) for duplicate callback id/timestamp replay attempts
- `validation_error` (`422`)
- `auth_invalid_api_key` (`401`)
- `insufficient_scope` (`403`) for missing push/job capabilities
- `rate_limited` (`429`) for SSE/onboarding throttle breaches

All errors use v2 standard envelope:

```json
{
  "api_version": "v2",
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "retryable": false,
    "details": {},
    "correlation_id": "corr_..."
  }
}
```

## Downstream Integration Patterns

Skriptoteket (UI-heavy):

- prefer SSE for live progress,
- fallback to polling on stream interruptions.

HuleEdu (mixed UI/backend):

- UI can consume SSE,
- backend orchestration can subscribe to webhooks for terminal events.

Projektveckor (backend-first):

- use webhook callbacks as primary integration path,
- verify `X-SCAL-Webhook-*` signature headers and timestamp window,
- use polling fallback for delivery outage recovery.

## KPI Targets

Push rollout acceptance targets:

- polling request-rate reduction `>=60%` for push-enabled clients,
- SSE propagation p95 `<= 2s`,
- webhook initial delivery p95 `<= 5s`,
- webhook success `>=100%` within first `3` attempts.

These metrics are operationalized in Task 56 runbook/observability deliverables.
