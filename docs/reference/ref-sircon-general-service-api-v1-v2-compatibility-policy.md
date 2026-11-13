---
type: reference
id: REF-SIRCON-GENERAL-service-api-v1-v2-compatibility-policy
title: Service API v1/v2 Compatibility Policy
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: draft
reference_kind: general
retired_ids:
- CONV-service-api-v1-v2-compatibility-policy
summary: Service API v1/v2 Compatibility Policy
---
## Overview

Source record: docs/converters/service_api_v1_v2_compatibility_policy.md

### Purpose

> Define the compatibility, versioning, and unification policy for Sir Convert-a-Lot service API v1
> and v2.
>
> This policy is obsolete after the v2-only clean break completed on 2026-02-28.
> The active conversion surface is now service API v2 only.

## Facts And Semantics

## Decisions And Interpretation

### Compatibility Policy

> ### Versioning Rules
>
> - v1 is **locked**:
>   - no new routes, formats, or semantics
>   - bug fixes are allowed only when they do not change the published contract
>   - any breaking change requires a new major API version (e.g. v3)
> - v2 is **additive-only**:
>   - new routes, optional fields, and new error codes are allowed
>   - breaking changes inside v2 are not allowed; breaking change => v3
>
> ### Shared Invariants (v1 and v2)
>
> These invariants are considered cross-version contract, even if implementation changes.
>
> 1. Correlation
>
> - Request header: `X-Correlation-ID` (optional, caller-supplied)
> - Response header: `X-Correlation-ID` (always returned)
> - Error payloads must include `error.correlation_id` and it must match the response header.
>
> 2. Error Envelope Shape
>
> All non-2xx responses return the standard error envelope:
>
> ```json
> {
>   "api_version": "v1|v2",
>   "error": {
>     "code": "string",
>     "message": "string",
>     "retryable": true,
>     "details": {},
>     "correlation_id": "corr_..."
>   }
> }
> ```
>
> The error envelope is intentionally compatible across versions; only `api_version` differs.
>
> 3. Idempotency Semantics (Create Job)
>
> - `Idempotency-Key` is required for `POST` job creation endpoints.
> - Scope is version-local and includes `(api_key, method, path, idempotency_key)`.
> - Replays:
>   - same key + same fingerprint returns the same `job_id`
>   - response header: `X-Idempotent-Replay: true`
>   - response status is `202` while the job is non-terminal, and `200` once terminal
> - Collisions:
>   - same key + different fingerprint returns `409`
>   - `error.code = "idempotency_key_reused_with_different_payload"`
>
> ### Unification Path (Without Breaking v1)
>
> Unification means converging semantics and documentation structure while keeping v1 stable.
>
> - Keep v1 routes and shapes unchanged.
> - Keep the error envelope and idempotency semantics aligned across versions via shared models and
>   shared tests.
> - Prefer documenting shared semantics once and linking from version-specific contract docs.
> - When a breaking or fully unified contract is needed, introduce v3 and keep v1 served for legacy
>   clients until an explicit deprecation decision is recorded.
