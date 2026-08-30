---
type: reference
id: REF-SIRCON-GENERAL-multi-format-conversion-service-api-v2
title: Multi-format Conversion Service API v2
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: general
retired_ids:
  - CONV-multi-format-conversion-service-api-v2
summary: Multi-format Conversion Service API v2
---

## Overview

## Facts And Semantics

## Decisions And Interpretation

## Historical Source Content

### Purpose

Define the active Service API v2 contract for Hemma-executed multi-format conversion jobs, including request validation, idempotency, progress, artifacts, checkpoints, cancellation, and resume. Route-specific extensions remain provider-neutral and fail closed.

### Base Conventions

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

Authentication model:

- One service API key is the only supported v2 auth secret.
- No internal-key lane or curated-app trusted-bundle lane is part of the
  active runtime contract.
  Error semantics:
- Missing or invalid key: `401 Unauthorized`, `error.code = "auth_invalid_api_key"`
- This contract does not treat curated app-owned downstream PDF artifacts as a

### Idempotency (Create Job)

Required header for `POST /v2/convert/jobs`:
Semantics:

- Scope: `(owner_scope, method, path, idempotency_key)`
- Request fingerprint: normalized request JSON + uploaded file SHA256 (+ optional resources SHA256
  and reference-docx SHA256 when present)
- TTL: 24h
- Same key + same fingerprint, active job (`queued|running`):
  - strict replay; return the same `job_id` and current state for that job
  - response header: `X-Idempotent-Replay: true`
- Same key + same fingerprint, successful job:
  - strict replay; return the same successful `job_id`
  - response header: `X-Idempotent-Replay: true`
- Same key + same fingerprint, failed job with `failure_retryable=false`:
  - strict replay; return the same failed `job_id`
  - expose `idempotency.current_attempt.failure_retryable=false`
  - response header: `X-Idempotent-Replay: true`
- Same key + same fingerprint, failed job with `failure_retryable=true`:
  - service-owned reattempt; atomically admit one fresh active attempt for the
    same logical request
  - update the idempotency pointer to the new active `job_id`
  - retain previous failed attempts in `idempotency.previous_attempts`
  - response header: `X-Idempotent-Replay: false`
- Same key + same fingerprint, canceled job:
  - strict replay; return the same canceled `job_id`
  - response header: `X-Idempotent-Replay: true`
- Same key + different fingerprint:
  - `409 Conflict`
  - `error.code = "idempotency_key_reused_with_different_payload"`
    Create-job responses include `idempotency` JSON metadata. Clients must prefer
    this body field over the header when deciding whether the response is a fresh
    admission, strict replay, or service-owned reattempt:

```json
{
  "state": "fresh_admission | strict_replay | service_reattempt",
  "idempotent_replay": false,
  "active_job_id": "jobv2_...",
  "attempt_count": 2,
  "current_attempt": {
    "job_id": "jobv2_new",
    "status": "queued",
    "failure_retryable": null
  },
  "previous_attempts": [
    {
      "job_id": "jobv2_failed",
      "status": "failed",
      "failure_retryable": true
    }
  ],
  "replayed_job_id": null,
  "reattempt_of_job_id": "jobv2_failed",
  "reason": "retryable_failed_terminal"
}
```

`fresh_admission` has `attempt_count=1` and no previous attempts.
`strict_replay` sets `idempotent_replay=true` and `replayed_job_id` to the
returned job. `service_reattempt` sets `reattempt_of_job_id` to the retryable
failed attempt that was superseded and sets a typed `reason`. Current reasons
are:

- `retryable_failed_terminal`: an old terminal failed attempt was service-owned
  retryable.
- `terminal_artifact_contract_incompatible`: a terminal succeeded attempt does
  not satisfy the route's current artifact compatibility contract.

### Supported Routes (Active Runtime)

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

### Route Extensions

- `audio -> transcript_bundle` executes canonical JSON transcription through
  the governed STT sidecar and may emit `txt`, `md`, `vtt`, and `srt`
  formatter artifacts. Admission validates owner scope, local-upload media,
  bounded public options, route capacity, GPU policy, and retention.
- `transcript_json -> transcript_bundle` replays formatting over one uploaded
  canonical transcript. It applies speaker overlays only to formatted outputs,
  runs outside the heavy conversion worker queue, and never emits a replacement
  canonical JSON artifact.

### Data Contracts (v2)

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
- `audio_probe_normalize_ms`
- `audio_diarization_ms`
- `audio_transcription_ms`
- `audio_alignment_ms`
- `audio_packaging_ms`
  v2 timing contract is strict:
- Only canonical keys above are accepted in v2 payloads and persisted diagnostics.
- Non-canonical timing keys are unsupported and ignored.
- `total_pages` (`int | null`)
- `processed_pages` (`int | null`) (monotonic; never decreases)
- `failed_pages` (`int | null`) (monotonic; never decreases)
- `percent_complete` (`float | null`) (monotonic; range `0..100`)
- `pages_per_minute` (`float | null`) (non-negative; best-effort)
- `eta_seconds` (`int | null`) (non-negative; best-effort)
  Audio transcription uses route-specific `audio_*` progress fields through its
  converter contract and OpenAPI update. It must not overload PDF page counters
  for processed duration or audio chunks. The `audio_pipeline_percent_complete`
  and `audio_pipeline_eta_seconds` fields are additive whole-pipeline measured
  estimates based only on explicit phase transitions and accepted chunk
  checkpoints; heartbeat freshness does not advance them.

### Metrics Label Policy (v2)

Prometheus metric labels must remain bounded-cardinality:

- Never use `job_id`, `X-Correlation-ID`, filename, or dynamic route values as metric labels.
- Use metric labels only for bounded dimensions (for example status/source/output/backend/policy).
- Correlate per-job investigations through logs/events (`X-Correlation-ID`, lifecycle events, webhook
  payloads), not metric labels.

### JobSpec (v2)

Field rules:

- `source.kind`: v2 requires `upload`
- `source.format`: `pdf | docx | md | html`
- `conversion.output_format`:
  - active runtime: `md | pdf | docx`
  - approved next extension (not yet implemented): `wav` for `md -> wav`
- `conversion.template`:
  - canonical DOCX selector shape:
    - `template_id` (required for template-selected DOCX conversions)
    - `version` (optional; omitted resolves latest active version)
  - full normative schema and governance:
- `conversion.css_filenames`:
  - only meaningful for `html -> pdf` and `md -> pdf`
  - filenames must exist within the extracted resources root when provided
- `conversion.page_css_mode`:
  - optional PDF-only page-CSS precedence selector
  - `preset_append`:
    - default behavior when omitted for PDF outputs
    - intended for quick one-off callers using typed `conversion.pdf_layout`
    - appends the generated preset stylesheet after caller CSS
  - `author_owned`:
    - intended for full downstream applications that own page setup in author CSS
    - forbids `conversion.pdf_layout`
    - does not append any service-owned preset page stylesheet
  - rejected for non-PDF outputs
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

### Resources Bundle (v2)

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

### Endpoints

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
  - `[]` for PDF routes where OCR was applicable but not executed,
  - `null` for routes where OCR is not applicable.
- Deferred OCR fields:
  - `ocr_languages_requested` is not part of result metadata; request intent is
    represented by `pdf_options.ocr_languages` in the submitted job spec.
  - `ocr_acceleration_used` is not part of result metadata; `acceleration_used`
    reports backend execution acceleration, and separate OCR-stage acceleration
    requires future observed telemetry before it can be published.
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
  `error.code = "job_not_succeeded"` with
  `error.details.status = "failed|canceled"`. Failed jobs also include
  `error.details.failure_retryable`.

### `GET /v2/convert/jobs/{job_id}/artifact`

Download the output artifact bytes for successful jobs.
The response content-type is derived from the stored artifact format:

- Markdown: `text/markdown`
- PDF: `application/pdf`
- DOCX: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Approved next extension (not yet implemented): WAV `audio/wav`

### `GET /v2/convert/jobs/{job_id}/artifact/partial`

Download a **partial markdown** artifact for long-running PDF routes when available.
Notes:

- This endpoint is **PDF-only**.
- The partial artifact is written incrementally during chunked conversion.
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
The success payload is the raw v2 PDF checkpoint document. The current schema
is `v2_pdf_checkpoint_v2`; earlier checkpoint payloads are not bridged. If a
retained checkpoint cannot be parsed under the current schema, the endpoint
returns `500` with `error.code = "checkpoint_invalid"` and resume/finalization
must fail closed rather than infer metadata.
Root fields:

- `schema_version`: literal `v2_pdf_checkpoint_v2`.
- `job_id`: source job id for the checkpoint payload.
- `updated_at`: RFC3339 timestamp for the latest checkpoint write.
- `total_pages`: total PDF page count when known.
- `chunk_size_pages`: configured chunk size for the PDF route.
- `processed_pages`: pages covered by succeeded chunk records.
- `failed_pages`: pages covered by failed chunk records.
- `chunks`: ordered or unordered chunk records; clients must sort by
  `(start_page,end_page,chunk_index)` when reconstructing order.
  Succeeded chunk records include:
- `chunk_index`, `start_page`, `end_page`: chunk identity and inclusive page range.
- `status`: `succeeded` or `failed`.
- `started_at`, `completed_at`: best-effort RFC3339 timestamps, nullable.
- `artifact_relpath`: job-relative markdown chunk artifact path.
- `sha256`: `sha256:<hex>` digest for the chunk artifact bytes.
- `size_bytes`: chunk artifact byte length.
- `backend_used`: observed backend label for the chunk.
- `acceleration_used`: observed acceleration label for the chunk.
- `ocr_enabled`: `true` only when OCR actually ran for the chunk.
- `ocr_engine_used`: observed OCR engine when `ocr_enabled=true`; otherwise `null`.
- `ocr_languages_used`: observed OCR languages when `ocr_enabled=true`; otherwise `[]`.
- `warnings`: backend/runtime warnings retained for the chunk.
- `phase_timings_ms`: canonical timing map retained for the chunk.
  Terminal finalization verifies every succeeded chunk artifact exists and matches
  the recorded `size_bytes` and `sha256`. Missing, corrupt, duplicate, or
  incomplete chunk coverage fails closed with a non-retryable checkpoint error
  instead of publishing a truncated artifact or inferred terminal metadata.
  Response matrix:
- `200 OK`: returns checkpoint JSON payload when available.
- `202 Accepted`: job exists (`queued|running|canceled`) but no checkpoint is available yet.
- `404 Not Found`: job missing/expired; `error.code = "job_not_found"`.
- `500 Internal Server Error`: checkpoint payload is unreadable or incompatible;
  `error.code = "checkpoint_invalid"`.
- `409 Conflict`: job is terminal and no checkpoint is available;
  `error.code = "checkpoint_not_available"`.

### `POST /v2/convert/jobs/{job_id}/cancel`

Request job cancellation.
Notes:

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

### Errors

- the standard v2 error envelope, and
- selected deterministic route error codes.
