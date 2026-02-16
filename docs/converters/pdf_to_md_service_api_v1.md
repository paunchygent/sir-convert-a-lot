---
type: converter
id: CONV-pdf-to-md-service-api-v1
title: PDF to Markdown Service API v1
status: active
created: '2026-02-11'
updated: '2026-02-14'
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

Backend compatibility matrix (Task 11):

- `backend_strategy="auto"` -> Docling backend.
- `backend_strategy="docling"` -> Docling backend.
- `backend_strategy="pymupdf"` is supported with constraints:
  - `execution.acceleration_policy` must be `cpu_only` (with rollout lock override enabled in
    runtime/test configuration when required).
  - `conversion.ocr_mode` must be `off`.
- Deterministic validation rejections:
  - `backend_strategy="pymupdf"` with `acceleration_policy in {"gpu_required","gpu_prefer"}`:
    - `422`
    - `error.code = "validation_error"`
    - `error.details = {"field":"conversion.backend_strategy","reason":"backend_incompatible_with_gpu_policy"}`
  - `backend_strategy="pymupdf"` with `ocr_mode in {"auto","force"}`:
    - `422`
    - `error.code = "validation_error"`
    - `error.details = {"field":"conversion.ocr_mode","reason":"backend_option_incompatible","backend":"pymupdf","supported":["off"]}`

Server policy constraints (Phase 0 lock):

- `SIR_CONVERT_A_LOT_ALLOW_CPU_ONLY` and `SIR_CONVERT_A_LOT_ALLOW_CPU_FALLBACK`
  are rejected when set to `1` in normal startup paths.
- CPU unlock behavior may be used only via explicit test configuration overrides in `ServiceConfig`.
- Requests resulting in CPU execution while lock is active must fail with `gpu_not_available`.
- Docling GPU runtime is fail-closed:
  - when GPU policy is requested but backend runtime probe is unavailable,
    request fails with deterministic `503 gpu_not_available` details:
    `{"reason":"backend_gpu_runtime_unavailable","backend":"docling","runtime_kind":"...","hip_version":"...","cuda_version":"..."}`
- Docling CPU execution is unsupported by invariant (service and direct backend paths).
  If a usable ROCm/CUDA runtime is unavailable, Docling conversion must fail closed.

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
      "pages_processed": 6,
      "last_heartbeat_at": "2026-02-11T17:00:10Z",
      "current_phase_started_at": "2026-02-11T17:00:09Z",
      "phase_timings_ms": {
        "backend_convert_ms": 2412,
        "normalize_ms": 17,
        "persist_ms": 8
      }
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

`conversion_metadata.acceleration_used` uses normalized value `"cuda"` for successful GPU execution,
including ROCm-backed torch runtimes.

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
  - includes fail-closed backend runtime details when applicable:
    `reason=backend_gpu_runtime_unavailable`

### `GET /v1/convert/jobs/{job_id}`

Returns job status and progress.

Progress diagnostics fields (`last_heartbeat_at`, `current_phase_started_at`,
`phase_timings_ms`) are included to distinguish slow conversions from stalled jobs.

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

### `GET /healthz`

Liveness endpoint for process/alive checks.

Behavior:

- Returns `200` when HTTP service is responsive.
- Does not enforce deploy-correctness invariants.

Response fields include:

- `status` (`"ok"`)
- `service_revision`
- `started_at`
- `data_root`
- `service_profile`

### `GET /readyz`

Readiness endpoint for deploy-correctness invariants.

Behavior:

- Returns `200` only when all readiness checks pass.
- Returns `503` fail-closed when any invariant fails.

Invariant checks:

- service revision matches expected revision,
- service profile matches expected entrypoint profile,
- prod/eval data-root configuration is isolated and profile-compatible.

Expected revision contract:

- expected revision is resolved at service startup from
  `SIR_CONVERT_A_LOT_EXPECTED_REVISION` (fallback: service startup revision),
- value is cached for deterministic readiness evaluation across requests.

Response fields include:

- `status` (`"ready"` or `"not_ready"`)
- `ready` (boolean)
- `service_revision`
- `expected_revision`
- `service_profile`
- `expected_service_profile`
- `data_root`
- `reasons` (array of structured readiness failures)

### `GET /metrics`

Prometheus metrics endpoint for HTTP observability.

Behavior:

- Returns `200` with `text/plain; version=0.0.4` content.
- Exposes route-normalized request count and latency metrics.

Current metric names:

- `sir_convert_a_lot_http_requests_total`
- `sir_convert_a_lot_http_request_duration_seconds`

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

Error details note:

- `409 job_not_succeeded` may include additional fields in `error.details` to aid internal debugging,
  for example:
  - `status`
  - `failure_code`
  - `failure_message`
  - `retryable`
- `422 validation_error` may include backend availability details during rollout,
  for example:
  - `field`
  - `reason`
  - `requested`
  - `available`
- `503 gpu_not_available` may include backend runtime probe details, for example:
  - `reason` (`backend_gpu_runtime_unavailable`)
  - `backend`
  - `runtime_kind`
  - `hip_version`
  - `cuda_version`

## Storage Layout (v1 Filesystem Backend)

Base directory (service env): `CONVERTER_STORAGE_ROOT`

Compatibility note:

- Implementation also supports `SIR_CONVERT_A_LOT_DATA_DIR` as an alias for the same storage root.
- When both are present, `CONVERTER_STORAGE_ROOT` is preferred.

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

## Markdown Normalization (Deterministic Line Breaks)

The service produces Markdown that is deterministic for the same input PDF and identical `JobSpec`.

Normalization is controlled by `job_spec.conversion.normalize`:

- `none`: Preserve backend output as-is (no reflow).
- `standard`: Normalize whitespace and blank lines in a Markdown-safe way without aggressive paragraph reflow.
- `strict`: Strong paragraph reflow to **width 100** for readability while preserving Markdown structure:
  - Do not reflow inside fenced code blocks.
  - Do not reflow Markdown tables.
  - Do not reflow headings or list markers.
  - Do not reflow blockquotes or horizontal rules.

## OCR Policy Mapping (Docling)

OCR behavior is controlled by `job_spec.conversion.ocr_mode`:

- `off`: single pass with OCR disabled.
- `force`: single pass with OCR enabled and full-page OCR forced.
- `auto`: deterministic two-step policy:
  1. Run first pass with OCR disabled.
  1. Compute:
     - `md_len = len(markdown.strip())`
     - `page_count = max(1, detected_page_count)`
     - `chars_per_page = md_len / page_count`
     - `low_confidence = true` when confidence grade is `poor` or `fair` (if confidence is available)
  1. Retry exactly once with OCR enabled + full-page OCR forced when any condition is true:
     - `md_len == 0`
     - `chars_per_page < 120`
     - `low_confidence == true`
