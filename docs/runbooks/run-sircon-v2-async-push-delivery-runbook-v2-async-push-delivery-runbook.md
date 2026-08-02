---
type: runbook
id: RUN-SIRCON-v2-async-push-delivery-runbook
title: V2 Async Push Delivery Runbook
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
summary: V2 Async Push Delivery Runbook
system: sir-convert-a-lot
retired_ids:
- RUN-v2-async-push-delivery
---
## Trigger

Source record: docs/runbooks/runbook-v2-async-push-delivery.md

### Purpose

> Provide deterministic operator procedures for v2 async push delivery:
>
> - SSE progress streaming,
> - webhook callback delivery with retries/DLQ,
> - polling fallback continuity,
> - KPI tracking and production rollback safety.

## Preconditions

### Runtime Flags

> Push controls are env-driven and can be toggled independently:
>
> - `SIR_CONVERT_A_LOT_ENABLE_SSE_STREAM=1|0`
> - `SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_ONBOARDING=1|0`
> - `SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_DELIVERY=1|0`
> - `SIR_CONVERT_A_LOT_WEBHOOK_SECRET_OVERLAP_SECONDS` (default `86400`)
> - `SIR_CONVERT_A_LOT_SSE_REPLAY_HORIZON_SECONDS` (default `86400`)
>
> Safe disable policy:
>
> - disable webhook delivery first,
> - keep onboarding + polling available,
> - disable SSE only if stream instability affects service SLO,
> - polling fallback remains canonical and must stay functional.

### Data Paths

> Assuming default `data_root=build/sir_convert_a_lot`, webhook delivery state is persisted at:
>
> - outbox queue: `build/sir_convert_a_lot/webhooks_v2/delivery/outbox/`
> - delivered receipts: `build/sir_convert_a_lot/webhooks_v2/delivery/delivered/`
> - dead-letter queue: `build/sir_convert_a_lot/webhooks_v2/delivery/dlq/`
>
> Webhook onboarding records are persisted at:
>
> - `build/sir_convert_a_lot/webhooks_v2/subscriptions/`

### Incident Triage

> ### 1) Backlog Growth
>
> Symptoms:
>
> - outbox count increases continuously,
> - delivered count stagnates,
> - callback latency rises.
>
> Commands:
>
> ```bash
> find build/sir_convert_a_lot/webhooks_v2/delivery/outbox -name '*.json' | wc -l
> find build/sir_convert_a_lot/webhooks_v2/delivery/delivered -name '*.json' | wc -l
> find build/sir_convert_a_lot/webhooks_v2/delivery/dlq -name '*.json' | wc -l
> ```
>
> Actions:
>
> 1. Verify callback endpoint reachability from service host.
> 1. Validate onboarding records are enabled and callback URLs are correct.
> 1. If retry storm is active, disable delivery via `SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_DELIVERY=0`,
>    keep polling fallback, and begin DLQ replay planning.
>
> ### 2) Retry Storm / DLQ Growth
>
> Symptoms:
>
> - repeated `http_5xx` or `network_error` failures in outbox entries,
> - DLQ count increasing.
>
> Actions:
>
> 1. Inspect one DLQ record for `attempt_count`, `last_error_class`, and `last_status_code`.
> 1. Fix remote callback availability/signature verification on consumer side.
> 1. Re-enable delivery only after callback lane stability is confirmed.
>
> ### 3) SSE Instability
>
> Symptoms:
>
> - repeated disconnects or elevated stream latency.
>
> Actions:
>
> 1. Confirm polling fallback is healthy (`GET /v2/convert/jobs/{job_id}`).
> 1. Temporarily disable SSE lane (`SIR_CONVERT_A_LOT_ENABLE_SSE_STREAM=0`) if required.
> 1. Keep webhook/polling lanes active.

### KPI Formula Template

> Use fixed windows (`baseline=7d` before push enable, `post=7d` after enable):
>
> 1. Poll reduction:
>    - formula: `1 - (poll_req_rate_post / poll_req_rate_baseline)`
>    - target: `>= 0.60`
> 1. SSE latency:
>    - source: SSE payload `sse_metrics.emit_to_send_ms`
>    - target: `p95 <= 2000ms`
> 1. Webhook initial delivery latency:
>    - source: delivered entry `delivery_latency_ms` for first-attempt deliveries
>    - target: `p95 <= 5000ms`
> 1. Webhook success within first 3 attempts:
>    - formula: `successful_deliveries_with_attempt_count<=3 / total_deliveries`
>    - target: `1.00` (100%)

## Steps

## Expected Results

### Verification Commands

> Run these from repo root via canonical local wrappers:
>
> ```bash
> pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2_sse.py
> pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2_webhook_onboarding.py
> pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_webhook_delivery_v2.py
> pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_integration_adapter_conformance.py::test_adapter_integration_smoke_submit_poll_fetch_without_gpu_runtime
> ```
>
> Expected outcomes:
>
> - SSE stream emits ordered events and `410 cursor_expired` for stale replay pointers.
> - onboarding CRUD/rotate/revoke semantics remain deterministic.
> - delivery worker proves success path, retry path, DLQ exhaustion path.
> - signature validation helper rejects invalid signature, stale timestamp, and replay attempts.

## Stop Conditions

### Rollout and Rollback

> ### Canary Rollout
>
> 1. Enable SSE and onboarding first, keep delivery disabled:
>    - `ENABLE_SSE_STREAM=1`, `ENABLE_WEBHOOK_ONBOARDING=1`, `ENABLE_WEBHOOK_DELIVERY=0`.
> 1. Validate onboarding + SSE contract tests.
> 1. Enable delivery for canary consumers:
>    - `ENABLE_WEBHOOK_DELIVERY=1`.
> 1. Track retry ratio + DLQ growth for one rollout window.
> 1. Expand rollout only when KPI trend is stable.
>
> ### Safe Rollback
>
> 1. Set `SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_DELIVERY=0`.
> 1. Confirm outbox stops draining and no new callback attempts are made.
> 1. Keep polling fallback active and notify downstream consumers.
> 1. Investigate and resolve callback/security issue before re-enable.

## Rollback

### Observability Contract

> Minimum operational signals:
>
> - queue depth: outbox entry count,
> - retries: entries with `attempt_count > 0`,
> - DLQ growth: number of DLQ entries over time,
> - callback latency: `delivery_latency_ms`,
> - SSE latency: `emit_to_send_ms` from SSE event payload.
>
> Alert thresholds (initial production defaults):
>
> - outbox depth > `100` for `10m` => alert `push_outbox_backlog_high`,
> - retry ratio (`retried / delivered`) > `0.20` for `10m` => alert `push_retry_storm`,
> - DLQ growth > `0` over `5m` => alert `push_dlq_growth`,
> - webhook delivery p95 > `5000ms` over `15m` => alert `push_webhook_latency_p95_high`,
> - SSE `emit_to_send_ms` p95 > `2000ms` over `15m` => alert `push_sse_latency_p95_high`.
