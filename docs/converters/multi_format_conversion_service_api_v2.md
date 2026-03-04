---
type: converter
id: CONV-multi-format-conversion-service-api-v2
title: Multi-format Conversion Service API v2
status: active
created: 2026-02-18
updated: 2026-03-04
owners:
  - platform
tags:
  - api
  - contract
  - v2
  - multi-format
links:
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/decisions/0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/converters/docx-template-catalog-contract-v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/multi_format_conversion_service_api_v2_async_push.md
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
  - docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md
---

## Purpose

Define the normative **service API v2** contract for multi-format conversions executed on Hemma.

Service API v2 is the single active conversion contract surface for:

- `pdf -> md`
- `docx -> md`
- `html -> md`
- `html -> pdf`
- `html -> docx`
- `docx -> pdf` (Pandoc -> HTML -> WeasyPrint)
- `md -> pdf` (via HTML intermediary)
- `md -> docx` (via HTML intermediary)
- `pdf -> docx` (service pipeline: `pdf -> md -> html -> docx`)

## Status

- v1 conversion routes: removed from runtime surface (2026-02-28)
- v2 contract: active (this document)

## Canonical Surfaces

- Service (HTTP): `scripts/sir_convert_a_lot/interfaces/http_api.py`
- Client (CLI): `scripts/sir_convert_a_lot/interfaces/cli_app.py`
- Downstream GUI integration guide: `docs/converters/downstream_integration_contract_v2.md`
- Async push extension contract:
  `docs/converters/multi_format_conversion_service_api_v2_async_push.md`

## Base Conventions

- Base path: `/v2`
- Content type: `application/json` unless otherwise noted
- Correlation:
  - Request header: `X-Correlation-ID` (optional, caller-supplied)
  - Response header: `X-Correlation-ID` (always returned)

### Authentication

Required header on all endpoints:

```http
X-API-Key: <service_api_key>
```

Error semantics:

- Missing or invalid key: `401 Unauthorized`, `error.code = "auth_invalid_api_key"`

### Idempotency (Create Job)

Required header for `POST /v2/convert/jobs`:

```http
Idempotency-Key: <opaque-client-key>
```

Semantics:

- Scope: `(api_key, method, path, idempotency_key)`
- Request fingerprint: normalized request JSON + uploaded file SHA256 (+ optional resources SHA256
  and reference-docx SHA256 when present)
- TTL: 24h
- Same key + same fingerprint:
  - Return same `job_id`
  - Return current state for that job
  - Response header: `X-Idempotent-Replay: true`
- Same key + different fingerprint:
  - `409 Conflict`
  - `error.code = "idempotency_key_reused_with_different_payload"`

## Supported Routes

Supported v2 conversions (service-executed on Hemma):

- `pdf -> md` (Docling/PyMuPDF pipeline)
- `docx -> md` (Pandoc -> deterministic Markdown normalization; `pipeline_used="docx_to_md_v2"`)
- `html -> md` (Pandoc -> deterministic Markdown normalization; `pipeline_used="html_to_md_v2"`)
- `docx -> pdf` (Pandoc -> HTML -> WeasyPrint)
- `html -> pdf` (WeasyPrint)
- `html -> docx` (Pandoc)
- `md -> pdf` (Pandoc -> HTML -> WeasyPrint)
- `md -> docx` (Pandoc -> HTML -> Pandoc)
- `pdf -> docx` (Docling/PyMuPDF -> Markdown -> HTML -> DOCX)

## Data Contracts (v2)

### JobStatus enum

Values:

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

### Job Progress (v2)

All job status payloads include a `job.progress` object with:

- `stage` (`string`): best-effort current stage marker (for example `queued`, `starting`,
  `converting`, `succeeded`, `failed`, `canceled`).
- `last_heartbeat_at` (`datetime | null`): liveness signal.
- `current_phase_started_at` (`datetime | null`): best-effort phase start marker.
- `phase_timings_ms` (`object`): best-effort stage timing counters.

PDF-only fields (per ADR-0005) are optional and may be `null` for non-PDF routes:

- `total_pages` (`int | null`)
- `processed_pages` (`int | null`) (monotonic; never decreases)
- `failed_pages` (`int | null`) (monotonic; never decreases)
- `percent_complete` (`float | null`) (monotonic; range `0..100`)
- `pages_per_minute` (`float | null`) (non-negative; best-effort)
- `eta_seconds` (`int | null`) (non-negative; best-effort)

### JobSpec (v2)

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "paper.pdf",
    "format": "pdf"
  },
  "conversion": {
    "output_format": "docx",
    "template": {
      "template_id": "academic-report",
      "version": "1.0.0"
    },
    "css_filenames": [],
    "reference_docx_filename": null
  },
  "pdf_options": {
    "backend_strategy": "auto",
    "ocr_mode": "auto",
    "table_mode": "accurate",
    "normalize": "strict"
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

- `source.kind`: v2 requires `upload`
- `source.format`: `pdf | docx | md | html`
- `conversion.output_format`: `md | pdf | docx`
- `conversion.template`:
  - canonical DOCX selector shape:
    - `template_id` (required for template-selected DOCX conversions)
    - `version` (optional; omitted resolves latest active version)
  - full normative schema and governance:
    - `docs/converters/docx-template-catalog-contract-v2.md`
- `conversion.css_filenames`:
  - only meaningful for `html -> pdf` and `md -> pdf`
  - filenames must exist within the extracted resources root when provided
- `conversion.pdf_layout`:
  - typed PDF-only page layout preset surface intended for downstream GUIs (paper size, orientation,
    and standard margins)
  - rejected for non-PDF outputs
- `conversion.reference_docx_filename`:
  - only meaningful for DOCX outputs
  - if provided, the referenced file must exist in the uploaded `reference_docx` part or the
    extracted resources root
  - rejected for routes with `output_format="md"`
  - must not be combined with `conversion.template` in the same request
- `pdf_options`:
  - required when `source.format="pdf"`
  - ignored when `source.format in {"docx","md","html"}`
- `execution.acceleration_policy`:
  - required when `source.format="pdf"` (governs the PDF->MD stage)
  - ignored otherwise

Route-specific JobSpec example (`docx -> md`):

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "input.docx",
    "format": "docx"
  },
  "conversion": {
    "output_format": "md",
    "css_filenames": [],
    "reference_docx_filename": null
  },
  "retention": {
    "pin": false
  }
}
```

Route-specific JobSpec example (`docx -> pdf`):

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "input.docx",
    "format": "docx"
  },
  "conversion": {
    "output_format": "pdf",
    "css_filenames": [],
    "pdf_layout": {
      "paper_size": "a4",
      "orientation": "portrait",
      "margins_mm": 12
    },
    "reference_docx_filename": null
  },
  "retention": {
    "pin": false
  }
}
```

Route-specific JobSpec example (`html -> md`):

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "index.html",
    "format": "html"
  },
  "conversion": {
    "output_format": "md",
    "css_filenames": [],
    "reference_docx_filename": null
  },
  "retention": {
    "pin": false
  }
}
```

Route-specific JobSpec example (`html -> pdf` with layout preset):

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "index.html",
    "format": "html"
  },
  "conversion": {
    "output_format": "pdf",
    "css_filenames": ["print.css"],
    "pdf_layout": {
      "paper_size": "a4",
      "orientation": "portrait",
      "margins_mm": 12
    },
    "reference_docx_filename": null
  },
  "retention": {
    "pin": false
  }
}
```

## Resources Bundle (v2)

For `md` and `html` inputs, the service may require additional resources (images, fonts, CSS) to
produce correct output.

`POST /v2/convert/jobs` supports an optional `resources` upload:

- content type: `application/zip`
- extracted to a job-scoped resources root
- safe extraction must reject path traversal (no `..` / absolute paths)
- safe extraction enforces zip-bomb limits (max members + max total/per-file uncompressed bytes)
- route guard for markdown outputs:
  - allowed for `html -> md`,
  - rejected for `pdf -> md` and `docx -> md`.

## Endpoints

### `POST /v2/convert/jobs`

Creates a conversion job.

Query parameters:

- `wait_seconds` (optional, integer `0..20`, default `0`)

Request (multipart form):

- `file`: upload (PDF/DOCX/Markdown/HTML)
- `job_spec`: v2 JobSpec JSON string
- `resources`: optional zip bundle
- `reference_docx`: optional reference docx for styling

Response:

- `200 OK` when job reaches terminal state within `wait_seconds`
- `202 Accepted` when job is queued/running

### `GET /v2/templates/docx`

List selection-ready DOCX templates for GUI discovery.

Response matrix:

- `200 OK`: returns `DocxTemplateListResponseV2`.

### `GET /v2/templates/docx/{template_id}`

Fetch all known versions for one template id.

Response matrix:

- `200 OK`: returns `DocxTemplateDetailResponseV2`.
- `404 Not Found`: template id does not exist; `error.code = "template_not_found"`.

### `GET /v2/templates/docx/{template_id}/versions/{version}`

Fetch one resolved template version record.

Response matrix:

- `200 OK`: returns `DocxTemplateVersionResponseV2`.
- `404 Not Found`: template id does not exist; `error.code = "template_not_found"`.
- `404 Not Found`: template version does not exist; `error.code = "template_version_not_found"`.

### `GET /v2/convert/jobs/{job_id}`

Fetch job status and links.

### `GET /v2/convert/jobs/{job_id}/result`

Fetch structured result metadata for successful jobs.

Binary artifacts are not returned inline. Clients should download them via the artifact endpoint.

For template-selected DOCX jobs, `result.conversion_metadata` includes:

- `template_id`
- `template_version`
- `template_artifact_sha256`

Response matrix:

- `200 OK`: job is `succeeded`; returns `JobResultResponseV2` with artifact + conversion metadata.
- `202 Accepted`: job is `queued|running`; returns `JobPendingResultResponseV2`.
- `404 Not Found`: job missing/expired; `error.code = "job_not_found"`.
- `409 Conflict`: job is terminal but not successful (`failed|canceled`);
  `error.code = "job_not_succeeded"` with `error.details = {"status":"failed|canceled"}`.

### `GET /v2/convert/jobs/{job_id}/artifact`

Download the output artifact bytes for successful jobs.

The response content-type is derived from the stored artifact format:

- Markdown: `text/markdown`
- PDF: `application/pdf`
- DOCX: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

Response matrix:

- `200 OK`: job is `succeeded`; returns the binary artifact bytes.
- `202 Accepted`: job is `queued|running`; returns `JobPendingResultResponseV2`.
- `404 Not Found`: job missing/expired; `error.code = "job_not_found"`.
- `409 Conflict`: job is terminal but not successful (`failed|canceled`);
  `error.code = "job_not_succeeded"` with `error.details = {"status":"failed|canceled"}`.

### `GET /v2/convert/jobs/{job_id}/artifact/partial`

Download a **partial markdown** artifact for long-running PDF routes when available.

Notes:

- This endpoint is **PDF-only**.
- The partial artifact is written incrementally during chunked conversion.
- The partial payload is explicitly annotated as partial (see ADR-0005).
- Partials/checkpoints expire with the job retention window; `retention.pin=true` extends availability.

Response matrix:

- `200 OK`: returns partial markdown bytes (`text/markdown`) when available.
- `202 Accepted`: job exists (`queued|running|canceled`) but no partial artifact is available yet.
- `404 Not Found`: job missing/expired; `error.code = "job_not_found"`.
- `409 Conflict`: job is terminal and no partial artifact is available, or job is `succeeded` and
  partial retrieval is rejected; `error.code` is one of:
  - `partial_artifact_not_available`
  - `job_succeeded_use_artifact`

### `GET /v2/convert/jobs/{job_id}/checkpoint`

Fetch the latest persisted checkpoint metadata for long-running PDF routes.

Response matrix:

- `200 OK`: returns checkpoint JSON payload when available.
- `202 Accepted`: job exists (`queued|running|canceled`) but no checkpoint is available yet.
- `404 Not Found`: job missing/expired; `error.code = "job_not_found"`.
- `409 Conflict`: job is terminal and no checkpoint is available;
  `error.code = "checkpoint_not_available"`.

### `POST /v2/convert/jobs/{job_id}/cancel`

Request job cancellation.

Response matrix:

- `202 Accepted`: job was `queued|running` and is now canceled; returns `JobRecordResponseV2`.
- `200 OK`: job was already `canceled`; returns `JobRecordResponseV2`.
- `404 Not Found`: job missing/expired; `error.code = "job_not_found"`.
- `409 Conflict`: job is terminal (`succeeded|failed`) and cannot be canceled;
  `error.code = "job_not_cancelable"`.

## Deterministic Route Errors (Selected)

- `docx -> md` unreadable/corrupt DOCX:
  - `422 Unprocessable Entity`
  - `error.code = "docx_unreadable"`
- `docx -> md` converter dependency missing:
  - `503 Service Unavailable`
  - `error.code = "pandoc_not_installed"`
  - `error.retryable = true`
- `docx -> md` converter execution failure:
  - `500 Internal Server Error`
  - `error.code = "docx_to_markdown_failed"`
  - `error.retryable = false`
- `html -> md` missing local resources:
  - `422 Unprocessable Entity`
  - `error.code = "html_resource_not_found"`
  - `error.details = {"missing_resources":[...]}`
- `html -> md` invalid local resource references:
  - `422 Unprocessable Entity`
  - `error.code = "html_resource_invalid"`
  - `error.details = {"invalid_resources":[...]}`
- `html -> md` converter dependency missing:
  - `503 Service Unavailable`
  - `error.code = "pandoc_not_installed"`
  - `error.retryable = true`
- `html -> md` converter execution failure:
  - `500 Internal Server Error`
  - `error.code = "html_to_markdown_failed"`
  - `error.retryable = false`

## Error Envelope (v2)

All non-2xx responses return a standard error envelope:

```json
{
  "api_version": "v2",
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "retryable": false,
    "details": {
      "errors": []
    },
    "correlation_id": "corr_..."
  }
}
```

The error model is intentionally compatible with v1, with `api_version` set to `v2`.
