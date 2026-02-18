---
type: converter
id: CONV-multi-format-conversion-service-api-v2
title: Multi-format Conversion Service API v2
status: draft
created: 2026-02-18
updated: 2026-02-18
owners:
  - platform
tags:
  - api
  - contract
  - v2
  - multi-format
links:
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/decisions/0002-multi-format-service-api-v2.md
---

## Purpose

Define the normative **service API v2** contract for multi-format conversions executed on Hemma.

Service API v1 remains locked to **PDF input + Markdown output only** (`pdf -> md`), and v2 is
the contract surface for:

- `html -> pdf`
- `html -> docx`
- `md -> pdf` (via HTML intermediary)
- `md -> docx` (via HTML intermediary)
- `pdf -> docx` (service pipeline: `pdf -> md -> html -> docx`)

## Status

- v1 contract: locked (2026-02-11)
- v2 contract: draft (this document)

## Canonical Surfaces

- Service (HTTP): `scripts/sir_convert_a_lot/interfaces/http_api.py`
- Client (CLI): `scripts/sir_convert_a_lot/interfaces/cli_app.py`

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

- `html -> pdf` (WeasyPrint)
- `html -> docx` (Pandoc)
- `md -> pdf` (Pandoc -> HTML -> WeasyPrint)
- `md -> docx` (Pandoc -> HTML -> Pandoc)
- `pdf -> docx` (Docling/PyMuPDF -> Markdown -> HTML -> DOCX)

Out of scope for v2 (explicit):

- expanding v1 beyond `pdf -> md`

## Data Contracts (v2)

### JobStatus enum

Same values as v1:

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

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
- `source.format`: `pdf | md | html`
- `conversion.output_format`: `pdf | docx`
- `conversion.css_filenames`:
  - only meaningful for `html -> pdf` and `md -> pdf`
  - filenames must exist within the extracted resources root when provided
- `conversion.reference_docx_filename`:
  - only meaningful for DOCX outputs
  - if provided, the referenced file must exist in the uploaded `reference_docx` part or the
    extracted resources root (implementation-defined; contract allows both)
- `pdf_options`:
  - required when `source.format="pdf"`
  - ignored when `source.format in {"md","html"}`
- `execution.acceleration_policy`:
  - required when `source.format="pdf"` (governs the PDF->MD stage)
  - ignored otherwise

## Resources Bundle (v2)

For `md` and `html` inputs, the service may require additional resources (images, fonts, CSS) to
produce correct output.

`POST /v2/convert/jobs` supports an optional `resources` upload:

- content type: `application/zip`
- extracted to a job-scoped resources root
- safe extraction must reject path traversal (no `..` / absolute paths)

## Endpoints

### `POST /v2/convert/jobs`

Creates a conversion job.

Query parameters:

- `wait_seconds` (optional, integer `0..20`, default `0`)

Request (multipart form):

- `file`: upload (PDF/Markdown/HTML)
- `job_spec`: v2 JobSpec JSON string
- `resources`: optional zip bundle
- `reference_docx`: optional reference docx for styling

Response:

- `200 OK` when job reaches terminal state within `wait_seconds`
- `202 Accepted` when job is queued/running

### `GET /v2/convert/jobs/{job_id}`

Fetch job status and links.

### `GET /v2/convert/jobs/{job_id}/result`

Fetch structured result metadata for successful jobs.

Binary artifacts are not returned inline. Clients should download them via the artifact endpoint.

### `GET /v2/convert/jobs/{job_id}/artifact`

Download the output artifact bytes for successful jobs.

The response content-type is derived from the stored artifact format:

- PDF: `application/pdf`
- DOCX: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

### `POST /v2/convert/jobs/{job_id}/cancel`

Request job cancellation.

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
