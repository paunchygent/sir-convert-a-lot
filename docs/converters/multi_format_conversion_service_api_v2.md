---
type: converter
id: CONV-multi-format-conversion-service-api-v2
title: Multi-format Conversion Service API v2
status: active
created: 2026-02-18
updated: 2026-06-09
owners:
  - platform
tags:
  - api
  - contract
  - v2
  - multi-format
links:
  - docs/decisions/0012-service-api-v2-current-state-authority-and-extension-boundary.md
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/decisions/0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/decisions/0008-curated-app-owned-pdf-exports-stay-out-of-sir-convert-v2.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/reference/ref-hemma-sidecar-tts-md-to-wav-contract-outline.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/converters/docx-template-catalog-contract-v2.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
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
- `digiexam_dxe -> examnet_migration_bundle` (DigiExam migration artifact
  bundle for authenticated Skriptoteket workflows)

Specialized route extensions are governed by route-specific converter
contracts. The DigiExam migration extension is defined in
`docs/converters/digiexam-migration-service-api-artifact-contract.md`; the
draft speech-to-text extension is defined in
`docs/converters/audio-transcription-service-api-artifact-contract.md`.

## Status

- v1 conversion routes: removed from runtime surface (2026-02-28)
- v2 contract: active (this document)
- active decision authority:
  `docs/decisions/0012-service-api-v2-current-state-authority-and-extension-boundary.md`

## Canonical Surfaces

- Service (HTTP): `scripts/sir_convert_a_lot/interfaces/http_api.py`
- Client (CLI): `scripts/sir_convert_a_lot/interfaces/cli_app.py`
- Downstream GUI integration guide: `docs/converters/downstream_integration_contract_v2.md`
- Async push extension contract:
  `docs/converters/multi_format_conversion_service_api_v2_async_push.md`
- DigiExam migration artifact-bundle contract:
  `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- Draft audio transcription artifact-bundle contract:
  `docs/converters/audio-transcription-service-api-artifact-contract.md`

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

Authentication model:

- One service API key is the only supported v2 auth secret.
- No internal-key lane or curated-app trusted-bundle lane is part of the
  active runtime contract.

Error semantics:

- Missing or invalid key: `401 Unauthorized`, `error.code = "auth_invalid_api_key"`
- This contract does not treat curated app-owned downstream PDF artifacts as a
  Sir Convert integration target; see ADR-0008 for that boundary.

### Idempotency (Create Job)

Required header for `POST /v2/convert/jobs`:

```http
Idempotency-Key: <opaque-client-key>
```

Semantics:

- Scope: `(owner_scope, method, path, idempotency_key)`
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

## Supported Routes (Active Runtime)

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
- `digiexam_dxe -> examnet_migration_bundle` (DigiExam `.dxe` parser -> IR ->
  Exam.net PDF + QTI package + named artifact bundle)

## Admission-Registered Route Extensions

The following v2 route extensions have accepted contracts but are not yet fully
service-executed conversion pipelines:

- `md -> wav` (sidecar-backed TTS on Hemma; see ADR-0006)
- `audio -> transcript_bundle` is admission-registered for Service API v2 job
  creation only. It validates request shape, owner scope, local-upload media
  suffixes, day-one public audio options, route capacity, GPU-required policy,
  and `retention.pin=false`, then leaves jobs queued until the later sidecar
  execution and `transcript_json` persistence slice lands. See ADR-0013 and
  `docs/converters/audio-transcription-service-api-artifact-contract.md`)

Important:

- These routes are approved for planning and contract publication.
- The audio route is admitted but **not yet executed** by the runtime.
- The public contracts remain provider-neutral and the TTS/STT backends must
  remain Hemma sidecars, not in-process dependencies in the main service image.
- Internal multi-backend TTS reuse is governed by ADR-0007; backend-native
  sidecar APIs are not the normative Sir-facing contract.
- ADR-0013 is accepted, and Task 355 registers the first admission-only audio
  route slice. Sidecar execution, route-specific progress, cancellation
  cleanup, and transcript artifact persistence are now governed by Task 356.
- For audio transcription, the first stable output authority is structured
  JSON; `txt`, `md`, `vtt`, and `srt` are later formatter artifacts over that
  JSON core.
- The audio route contract defines STT sidecar health/capability endpoints,
  fail-closed diarization, untrusted media limits, short retention classes, and
  route-specific audio progress fields.
- Product/browser access uses the existing HuleEdu Gateway `/sir-convert`
  edge; direct anonymous public access remains out of scope.

The implemented DigiExam migration route keeps `.dxe` as the required
structure source and uses a route-specific named artifact bundle rather than
the generic singular artifact as its product-facing contract.

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

v2 timing contract is strict:

- Only canonical keys above are accepted in v2 payloads and persisted diagnostics.
- Non-canonical timing keys are unsupported and ignored.

PDF-only fields (per ADR-0005) are optional and may be `null` for non-PDF routes:

- `total_pages` (`int | null`)
- `processed_pages` (`int | null`) (monotonic; never decreases)
- `failed_pages` (`int | null`) (monotonic; never decreases)
- `percent_complete` (`float | null`) (monotonic; range `0..100`)
- `pages_per_minute` (`float | null`) (non-negative; best-effort)
- `eta_seconds` (`int | null`) (non-negative; best-effort)

Draft audio transcription work must add route-specific `audio_*` progress
fields through its converter contract and OpenAPI update before runtime
registration. It must not overload PDF page counters for processed duration or
audio chunks.

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
- `source.format`: `pdf | docx | md | html`; route-specific extension:
  `digiexam_dxe`
- `conversion.output_format`:
  - active runtime: `md | pdf | docx`
  - route-specific extension: `examnet_migration_bundle`
  - approved next extension (not yet implemented): `wav` for `md -> wav`
- `conversion.template`:
  - canonical DOCX selector shape:
    - `template_id` (required for template-selected DOCX conversions)
    - `version` (optional; omitted resolves latest active version)
  - full normative schema and governance:
    - `docs/converters/docx-template-catalog-contract-v2.md`
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
- `tts_options`:
  - not part of the active runtime yet
  - reserved for the approved `md -> wav` extension
  - planned phase-1 shape:
    - `voice`
    - `language`
    - `style_instructions`
    - `normalize_for_speech`
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
  - approved next extension (`md -> wav` only; not yet implemented):
    - `execution` becomes required,
    - only `acceleration_policy="gpu_required"` is accepted,
    - `gpu_prefer` and `cpu_only` are rejected.

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
    "page_css_mode": "preset_append",
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

Route-specific JobSpec example (`html -> pdf` with author-owned page CSS):

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
    "page_css_mode": "author_owned",
    "reference_docx_filename": null
  },
  "retention": {
    "pin": false
  }
}
```

In the `author_owned` example above, the caller's uploaded CSS is authoritative
for `@page` size/orientation/margins. `conversion.pdf_layout` must be omitted.

Route-specific JobSpec example (`html -> pdf`):

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "poster.html",
    "format": "html"
  },
  "conversion": {
    "output_format": "pdf",
    "css_filenames": ["poster.css"],
    "reference_docx_filename": null
  },
  "retention": {
    "pin": false
  }
}
```

Approved next-route JobSpec draft (`md -> wav`; not yet implemented):

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "lesson.md",
    "format": "md"
  },
  "conversion": {
    "output_format": "wav",
    "css_filenames": [],
    "reference_docx_filename": null
  },
  "tts_options": {
    "voice": "teacher-clear-01",
    "language": "en",
    "style_instructions": "Read clearly as a teacher with a moderate pace.",
    "normalize_for_speech": "auto"
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

## Approved `md -> wav` Contract Draft (Not Yet Implemented)

The approved phase-1 `md -> wav` contract draft is:

- source:
  - `source.format="md"`
- target:
  - `conversion.output_format="wav"`
- execution:
  - sidecar-backed TTS only,
  - fail-closed,
  - `gpu_required` only in phase 1.

Planned phase-1 `tts_options` semantics:

- `voice`: provider-neutral preset voice identifier
- `language`: caller intent only; runtime validates against the configured sidecar profile
- `style_instructions`: bounded free-text style guidance
- `normalize_for_speech`: `auto | strict`

Planned success expectations:

- artifact filename suffix: `.wav`
- artifact content type: `audio/wav`
- provider-neutral metadata additions under `result.conversion_metadata`:
  - `tts_voice_used`
  - `tts_language_used`
  - bounded `backend_used` such as `tts_sidecar`

Planned stage markers:

- `queued`
- `starting`
- `normalizing`
- `synthesizing`
- `packaging`
- `succeeded`
- `failed`
- `canceled`

Phase-1 exclusions:

- voice cloning
- reference-audio uploads
- Swedish quality guarantee
- compressed-format contract requirement

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
  `error.code = "job_not_succeeded"` with `error.details = {"status":"failed|canceled"}`.

### `GET /v2/convert/jobs/{job_id}/artifact`

Download the output artifact bytes for successful jobs.

The response content-type is derived from the stored artifact format:

- Markdown: `text/markdown`
- PDF: `application/pdf`
- DOCX: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Approved next extension (not yet implemented): WAV `audio/wav`
- DigiExam migration route extension: the singular artifact may return
  `artifact-bundle.json` as `application/json`, while consumers should use the
  route-specific named artifact endpoints defined in
  `docs/converters/digiexam-migration-service-api-artifact-contract.md`.

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
