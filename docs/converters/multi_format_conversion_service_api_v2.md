---
type: converter
id: CONV-multi-format-conversion-service-api-v2
title: Multi-format Conversion Service API v2
status: active
created: 2026-02-18
updated: 2026-03-05
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
  - docs/converters/multi_format_conversion_service_api_v2_errors.md
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
- `phase_timings_ms` (`object`): canonical best-effort stage timing counters.

Canonical v2 timing keys in `phase_timings_ms`:

- `ocr_layout_extract_ms`
- `markdown_normalize_ms`
- `formula_enrichment_ms`
- `checkpoint_persist_ms`
- `final_artifact_persist_ms`
- `chunk_total_ms`
- `conversion_total_ms`

Compatibility alias mapping (accepted as input, normalized on persistence/response):

- `backend_convert_ms` -> `ocr_layout_extract_ms`
- `normalize_ms` -> `markdown_normalize_ms`
- `chunk_elapsed_ms` -> `chunk_total_ms`
- `persist_ms` -> `final_artifact_persist_ms`
- `conversion_attempt_ms` -> `conversion_total_ms`

PDF-only fields (per ADR-0005) are optional and may be `null` for non-PDF routes:

- `total_pages` (`int | null`)
- `processed_pages` (`int | null`) (monotonic; never decreases)
- `failed_pages` (`int | null`) (monotonic; never decreases)
- `percent_complete` (`float | null`) (monotonic; range `0..100`)
- `pages_per_minute` (`float | null`) (non-negative; best-effort)
- `eta_seconds` (`int | null`) (non-negative; best-effort)

### Metrics Label Policy (v2)

Prometheus metric labels must remain bounded-cardinality:

- Never use `job_id`, `X-Correlation-ID`, filename, or dynamic route values as metric labels.
- Use metric labels only for bounded dimensions (for example status/source/output/backend/policy).
- Correlate per-job investigations through logs/events (`X-Correlation-ID`, lifecycle events, webhook
  payloads), not metric labels.

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
    "ocr_engine": "auto",
    "ocr_languages": [],
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
  - subfields:
    - `backend_strategy`: `auto|docling|pymupdf`
    - `ocr_mode`: `off|force|auto`
    - `ocr_engine`: `auto|easyocr|tesseract_cli`
      - `auto` delegates to runtime defaults.
    - `ocr_languages`: list of BCP47/ISO639-1 tags (for example `["sv","en"]` or `["sv-SE","en"]`)
      - empty list delegates to runtime defaults.
      - mapping is engine-specific:
        - EasyOCR uses the ISO639-1 primary tags (for example `sv`, `en`)
        - Tesseract CLI maps `sv -> swe`, `en -> eng` and rejects unsupported tags.
    - `table_mode`: `fast|accurate`
    - `normalize`: `none|standard|strict`
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

Telemetry and acceleration evidence fields in `result.conversion_metadata`:

- `acceleration_policy_requested` (`string | null`):
  - echoes requested execution policy when provided in job spec (PDF routes),
  - `null` for routes where execution policy is not applicable.
- `acceleration_used` (`string | null`):
  - effective accelerator channel used by the conversion backend (`cpu`, `cuda`, or `null`).
- `ocr_enabled` (`bool | null`):
  - `true` when OCR was executed for the PDF->MD stage,
  - `false` when OCR was disabled or not required,
  - `null` for routes where OCR is not applicable.
- `ocr_engine_used` (`string | null`):
  - effective OCR engine used when OCR is enabled (`auto|easyocr|tesseract_cli`),
  - `null` when OCR is not executed or not applicable.
- `ocr_languages_used` (`list[string] | null`):
  - best-effort normalized OCR language tags used for the OCR stage (for example `["sv","en"]`),
  - `null` when OCR is not executed or not applicable.
- `gpu_runtime_kind` (`string | null`):
  - best-effort runtime kind observed for GPU-backed jobs (`rocm`, `cuda`, or `null`).
- `gpu_device_count` (`int | null`):
  - best-effort observed device count from runtime probe.
- `gpu_busy_percent` (`int | null`):
  - best-effort utilization snapshot at/near terminalization.
- `gpu_memory_used_percent` (`int | null`):
  - best-effort memory pressure snapshot at/near terminalization.

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

Notes:

- For long-running PDF routes, cancellation is **cancel-with-save** (ADR-0005):
  - the service stops processing at the next safe checkpoint boundary,
  - the latest valid checkpoint remains available via `/checkpoint`,
  - partial output (when any chunks have completed) is retrievable via `/artifact/partial`.

Response matrix:

- `202 Accepted`: job was `queued|running` and is now canceled; returns `JobRecordResponseV2`.
- `200 OK`: job was already `canceled`; returns `JobRecordResponseV2`.
- `404 Not Found`: job missing/expired; `error.code = "job_not_found"`.
- `409 Conflict`: job is terminal (`succeeded|failed`) and cannot be canceled;
  `error.code = "job_not_cancelable"`.

### `POST /v2/convert/jobs/{job_id}/resume`

Resume a long-running PDF job from its latest valid checkpoint (ADR-0005).

Notes:

- This endpoint is **PDF-only**.
- Resume always creates a **new** job id and never mutates the original job record.
- Resume requires `Idempotency-Key` and is idempotent per `(api_key, job_id, Idempotency-Key)`.

Response matrix:

- `200 OK`: idempotent replay; returns the resumed job `JobRecordResponseV2`.
- `202 Accepted`: resume accepted; returns the resumed job `JobRecordResponseV2`.
- `404 Not Found`: job missing/expired; `error.code = "job_not_found"`.
- `409 Conflict`: resume not allowed (missing checkpoint, unsupported job status, or unsupported route);
  `error.code` is one of:
  - `resume_not_available`
  - `resume_checkpoint_missing`

## Errors

See `docs/converters/multi_format_conversion_service_api_v2_errors.md` for:

- the standard v2 error envelope, and
- selected deterministic route error codes.
