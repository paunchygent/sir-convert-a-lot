---
type: converter
id: CONV-pdf-to-md-service-api-v1
title: PDF to Markdown Service API v1
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - api
  - contract
  - pdf-to-md
links:
  - docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md
  - docs/backlog/stories/story-03-01-lock-v1-contract-and-no-hassle-local-dev-ux.md
---

## Status

- Phase 0 contract: **locked** (2026-02-11)
- Primary deployment target: Hemma
- Architecture direction: HTTP async first, queue-worker compatible
- Story 003a implementation: **delivered** in `scripts/sir_convert_a_lot/service.py`

## Canonical Local Tooling

- Service run command: `pdm run serve:sir-convert-a-lot`
- Client command: `pdm run convert-a-lot convert <source> --output-dir <target>`
- Alias command: `pdm run sir-convert-a-lot convert <source> --output-dir <target>`
- Local UX guide: `docs/converters/sir_convert_a_lot.md`

## Decision Lock (Phase 0)

1. Endpoint shape

- No separate synchronous endpoint in v1.
- Use async job endpoints only.
- `POST /v1/convert/jobs` supports optional bounded wait (`wait_seconds`) for small files.

2. Auth

- Service is internal-network scoped and requires `X-API-Key` on all endpoints.

3. Storage backend v1

- Filesystem-backed job storage with a storage adapter boundary.
- Object storage is a v2 backend option without API contract changes.

4. Retention

- Raw uploads: 24h default TTL.
- Result artifacts + manifests: 7d default TTL.
- Pinned jobs are exempt until manually unpinned.

5. Acceleration policy

- **GPU-first is mandatory default objective**.
- Initial v1 rollout enforces GPU execution path before any CPU fallback is enabled.
- CPU fallback is decision-gated and may only be enabled after documented GPU exploration and benchmarks.
- CPU unlock env vars are disabled in standard startup paths during rollout lock.

## Base Conventions

- Base path: `/v1`
- Content type: `application/json` unless otherwise noted
- Timestamps: RFC3339 UTC (`2026-02-11T17:00:00Z`)
- Correlation:
  - Request header: `X-Correlation-ID` (optional, caller-supplied)
  - Response header: `X-Correlation-ID` (always returned)

## Authentication

Required header on all endpoints:

```http
X-API-Key: <service_api_key>
```

Error semantics:

- Missing or invalid key: `401 Unauthorized`, `error.code = "auth_invalid_api_key"`

## Idempotency (Create Job)

Required header for `POST /v1/convert/jobs`:

```http
Idempotency-Key: <opaque-client-key>
```

Semantics:

- Scope: `(api_key, method, path, idempotency_key)`
- Request fingerprint: normalized request JSON + uploaded PDF SHA256
- TTL: 24h
- Same key + same fingerprint:
  - Return same `job_id`
  - Return current state for that job
  - Response header: `X-Idempotent-Replay: true`
- Same key + different fingerprint:
  - `409 Conflict`
  - `error.code = "idempotency_key_reused_with_different_payload"`

## Data Contracts

### JobStatus enum

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

### JobSpec (v1)

```json
{
  "api_version": "v1",
  "source": {
    "kind": "upload",
    "filename": "paper.pdf"
  },
  "conversion": {
    "output_format": "md",
    "backend_strategy": "auto",
    "ocr_mode": "auto",
    "table_mode": "fast",
    "normalize": "standard"
  },
  "execution": {
    "acceleration_policy": "gpu_required",
    "priority": "normal",
    "document_timeout_seconds": 1800
  },
  "retention": {
    "pin": false
  }
}
```

Field rules:

- `source.kind`: v1 requires `upload`
- `conversion.output_format`: `md` only in v1
- `conversion.backend_strategy`: `auto | docling | pymupdf`
- `conversion.ocr_mode`: `auto | off | force`
- `conversion.table_mode`: `fast | accurate`
- `conversion.normalize`: `none | standard | strict`
- `execution.acceleration_policy`: `gpu_required | gpu_prefer | cpu_only`
- `execution.priority`: `normal | high`
- `execution.document_timeout_seconds`: integer `30..7200`
- `retention.pin`: boolean (default `false`)

Server policy constraints (Phase 0 lock):

- `SIR_CONVERT_A_LOT_ALLOW_CPU_ONLY` and `SIR_CONVERT_A_LOT_ALLOW_CPU_FALLBACK`
  are rejected when set to `1` in normal startup paths.
- CPU unlock behavior may be used only via explicit test configuration overrides in `ServiceConfig`.
- Requests resulting in CPU execution while lock is active must fail with `gpu_not_available`.

### JobRecord (status payload)

```json
{
  "api_version": "v1",
  "job": {
    "job_id": "job_01K2S8CXH3BWV7S6E5B7P4Y2ZR",
    "status": "running",
    "created_at": "2026-02-11T17:00:00Z",
    "updated_at": "2026-02-11T17:00:10Z",
    "expires_at": "2026-02-18T17:00:00Z",
    "source_filename": "paper.pdf",
    "progress": {
      "stage": "layout_analysis",
      "pages_total": 18,
      "pages_processed": 6
    },
    "links": {
      "self": "/v1/convert/jobs/job_01K2S8CXH3BWV7S6E5B7P4Y2ZR",
      "result": "/v1/convert/jobs/job_01K2S8CXH3BWV7S6E5B7P4Y2ZR/result",
      "cancel": "/v1/convert/jobs/job_01K2S8CXH3BWV7S6E5B7P4Y2ZR/cancel"
    }
  }
}
```

### JobResult (success payload)

```json
{
  "api_version": "v1",
  "job_id": "job_01K2S8CXH3BWV7S6E5B7P4Y2ZR",
  "status": "succeeded",
  "result": {
    "artifact": {
      "markdown_filename": "paper.md",
      "size_bytes": 182944,
      "sha256": "f4f2b6d0..."
    },
    "conversion_metadata": {
      "backend_used": "docling",
      "acceleration_used": "cuda",
      "ocr_enabled": false,
      "table_mode": "fast",
      "options_fingerprint": "sha256:ac89..."
    },
    "warnings": [
      "Detected low-confidence text in pages 15-16"
    ]
  }
}
```

## Endpoints

### `POST /v1/convert/jobs`

Creates a conversion job.

Query parameters:

- `wait_seconds` (optional, integer `0..20`, default `0`)

Request:

- `Content-Type: multipart/form-data`
- Part `file`: PDF binary (`application/pdf`)
- Part `job_spec`: JSON matching `JobSpec`

Responses:

- `202 Accepted`: job queued/running
- `200 OK`: job reached terminal state within `wait_seconds`
- `400 Bad Request`: malformed request/spec
- `401 Unauthorized`: invalid API key
- `409 Conflict`: idempotency reuse conflict
- `413 Payload Too Large`: file exceeds configured limit
- `415 Unsupported Media Type`: non-PDF upload
- `422 Unprocessable Entity`: unreadable/corrupt PDF
- `429 Too Many Requests`: rate limit
- `503 Service Unavailable`: GPU required but unavailable

### `GET /v1/convert/jobs/{job_id}`

Returns job status and progress.

Responses:

- `200 OK`: `JobRecord`
- `401 Unauthorized`
- `404 Not Found`: unknown/expired job

### `GET /v1/convert/jobs/{job_id}/result`

Returns terminal result for succeeded jobs.

Query parameters:

- `inline` (optional, boolean, default `false`)

Behavior:

- If `inline=false`: returns `JobResult` metadata (artifact info only)
- If `inline=true`: includes `markdown_content` when artifact size \<= configured inline limit

Responses:

- `200 OK`: result payload
- `202 Accepted`: job not yet terminal
- `401 Unauthorized`
- `404 Not Found`: job unknown/expired
- `409 Conflict`: job terminal but not `succeeded`
- `413 Payload Too Large`: inline requested but result exceeds inline limit

### `POST /v1/convert/jobs/{job_id}/cancel`

Requests cancellation for `queued` or `running` jobs.

Responses:

- `202 Accepted`: cancellation requested
- `200 OK`: already canceled (idempotent)
- `401 Unauthorized`
- `404 Not Found`
- `409 Conflict`: terminal state cannot be canceled

## Standard Error Model

All non-2xx responses return:

```json
{
  "api_version": "v1",
  "error": {
    "code": "validation_error",
    "message": "Field conversion.table_mode must be one of: fast, accurate",
    "retryable": false,
    "details": {
      "field": "conversion.table_mode"
    },
    "correlation_id": "corr_01K2S8..."
  }
}
```

Canonical error codes:

- `auth_invalid_api_key`
- `validation_error`
- `unsupported_media_type`
- `payload_too_large`
- `pdf_unreadable`
- `idempotency_key_reused_with_different_payload`
- `job_not_found`
- `job_not_ready`
- `job_not_succeeded`
- `job_expired`
- `gpu_not_available`
- `rate_limited`
- `internal_error`

## Storage Layout (v1 Filesystem Backend)

Base directory (service env): `CONVERTER_STORAGE_ROOT`

```text
jobs/
  <job_id>/
    raw/
      input.pdf
    artifacts/
      output.md
    logs/
      run.log
    manifest.json
```

`manifest.json` minimum fields:

- `job_id`
- `job_spec` (normalized)
- `status`
- `timestamps` (`created_at`, `updated_at`, `completed_at`)
- `result_metadata` or `error`
- `retention` (`raw_expires_at`, `artifact_expires_at`, `pinned`)

## Retention and Cleanup

- Raw files deleted after 24h by sweeper job
- Artifacts/manifests deleted after 7d by sweeper job
- Pinned jobs skipped by sweeper
- Expired jobs return `404` with `error.code = "job_expired"`

## Queue Compatibility Guarantees

This v1 schema is transport-independent:

- HTTP layer validates input and emits `JobSpec`
- Executor consumes `JobSpec`, produces `JobResult`
- Future queue worker adoption must preserve endpoint and payload contract unchanged
