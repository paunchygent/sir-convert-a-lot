---
type: converter
id: CONV-downstream-integration-contract-v2
title: Downstream Integration Contract v2
status: active
created: 2026-02-28
updated: 2026-06-14
owners:
  - platform
tags:
  - v2
  - integration
  - downstream
  - contract
links:
  - docs/decisions/0012-service-api-v2-current-state-authority-and-extension-boundary.md
  - docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/docx-template-catalog-contract-v2.md
  - docs/converters/sir_convert_a_lot.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - docs/reference/ref-stt-proof-lanes-and-admission-operations.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/decisions/0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md
---

## Purpose

Define one downstream-facing, GUI-ready integration contract for:

- Skriptoteket
- HuleEdu
- Projektveckor

This document is the canonical integration guide for route usage, request assembly, job lifecycle
handling, template discovery, and deterministic error handling on service API v2.

## Contract Authority and Version Policy

- API contract authority: `docs/converters/multi_format_conversion_service_api_v2.md`
- DigiExam migration API/artifact contract authority:
  `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- Template authority: `docs/converters/docx-template-catalog-contract-v2.md`
- CLI usage authority: `docs/converters/sir_convert_a_lot.md`

Version lock:

- Conversion integrations are v2-only.
- `/v1/convert/jobs*` is not part of the supported runtime surface.
- No fallback route family is supported for downstream integrations.

## Canonical Headers and Multipart Contract

Current service-v2 transport headers:

- `X-API-Key`: service secret
- `Idempotency-Key`: required for `POST /v2/convert/jobs`

Current migration rule:

- `X-API-Key` remains the current transport credential for direct v2 service
  calls.
- Under ADR-0009, user-originated product work must also carry HuleEdu
  `InternalIdentityContextV1` with audience `sir-convert-a-lot` once the
  Gateway/internal identity cutover lands.
- The Sir Convert authorization profile is
  `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.
- `X-API-Key` must not remain the long-term job/artifact ownership boundary
  for user-originated workloads.

Optional header:

- `X-Correlation-ID`: caller trace id; service always returns this header

`POST /v2/convert/jobs` multipart parts:

- `file`: required source upload
- `job_spec`: required JSON string (v2 schema)
- `resources`: optional zip (route-constrained)
- `reference_docx`: optional DOCX (route-constrained)
- route-specific optional companion parts only where a route-specific contract
  defines them.

Deterministic route constraints:

- `resources` is allowed only for `html -> md` when `output_format="md"`.
- `reference_docx` is not allowed for `output_format="md"`.
- `conversion.template` and `reference_docx` must not be combined.
- DigiExam migration is the current route-specific exception: it accepts
  `graded_result_pdf` and `parity_pdf` companion parts under
  `docs/converters/digiexam-migration-service-api-artifact-contract.md` and
  rejects generic `resources` or `reference_docx`.

## Capability Matrix (Implemented v2 Routes)

| Source | Target | Route key | Notes |
| --- | --- | --- | --- |
| `pdf` | `md` | `pdf -> md` | Requires `pdf_options` + `execution` |
| `docx` | `md` | `docx -> md` | Pandoc path, deterministic normalization |
| `html` | `md` | `html -> md` | Supports optional `resources` |
| `md` | `docx` | `md -> docx` | Supports template selector |
| `md` | `pdf` | `md -> pdf` | Service pipeline |
| `html` | `pdf` | `html -> pdf` | Service pipeline |
| `html` | `docx` | `html -> docx` | Service pipeline |
| `pdf` | `docx` | `pdf -> docx` | Service pipeline |
| `docx` | `pdf` | `docx -> pdf` | Service pipeline |

## Specialized Routes

These routes have accepted or active contracts with route-specific readiness
states:

| Source | Target | Route key | State | Contract |
| --- | --- | --- | --- | --- |
| `digiexam_dxe` | `examnet_migration_bundle` | `digiexam_dxe -> examnet_migration_bundle` | Runtime route | `docs/converters/digiexam-migration-service-api-artifact-contract.md` |
| `audio` | `transcript_bundle` | `audio -> transcript_bundle` | Runtime JSON execution plus optional formatter artifacts | `docs/converters/audio-transcription-service-api-artifact-contract.md` |
| `transcript_json` | `transcript_bundle` | `transcript_json -> transcript_bundle` | Fast-lane formatter replay over saved canonical JSON plus speaker overlays | `docs/converters/audio-transcription-service-api-artifact-contract.md` |

For audio transcription, product/browser traffic uses the same HuleEdu Gateway
`/sir-convert/v2/convert/...` product edge as governed Sir Convert conversion
jobs. The initial product contract is authenticated Gateway plus tunnel API
only; no public grant or anonymous transcription lane is part of the accepted
ADR-0013 boundary. Task 356 provides the first runtime surface for canonical
`transcript_json`; Task 358 adds optional product-neutral `transcript_txt`,
`transcript_md`, `transcript_vtt`, and `transcript_srt` artifacts over that
canonical JSON. Product-owned durable transcript saves, search, sharing,
teacher-facing labels, and workflow-specific derivatives remain downstream
work.
If browser upload fails around `/sir-convert/v2/convert/jobs`, downstreams
should treat CORS/network errors as symptoms until edge, Gateway, and Sir
Convert timestamps are compared. Sir Convert audio admission is required to
accept or reject async `wait_seconds=0` jobs without retained-job scans sweeping
the job store once per retained job.

For overlay-aware replay, HuleEdu forwards the same v2 job lifecycle through
`/sir-convert/v2/convert/jobs*` and must not rewrite Sir Convert result,
manifest, or artifact responses. Skriptoteket submits saved canonical
`transcript_json_v1` plus `transcript_formatter_options`, owns durable speaker
overlay intent and product filenames, and consumes only the returned
`transcript_txt`, `transcript_md`, `transcript_vtt`, and `transcript_srt`
artifacts. Replay artifact requests use exact lowercase values, speaker overlay
labels are exact case-sensitive canonical inventory keys, and replay specs must
not include `pdf_options` or `execution`. Replay does not return a
`transcript_json` named artifact. Replay uses the existing
`POST /v2/convert/jobs` contract, but the producer executes it outside the
generic heavy conversion worker queue; `wait_seconds=0` returns a terminal
success or terminal fail-closed replay job when the request is admitted.

### Skriptoteket PR-0351 STT Progress Contract

For `audio -> transcript_bundle`, downstream callers should render progress
from `job.progress` on the existing create/poll lifecycle. The exact public
fields for Skriptoteket `PR-0351` are:

| Field | Downstream meaning |
| --- | --- |
| `stage` | Safe phase marker. `diarizing` is emitted before the blocking sidecar diarization call starts. |
| `last_heartbeat_at` | Liveness only; do not use it to advance progress bars. |
| `audio_total_media_seconds` | Observed source media duration after probe/normalization succeeds. |
| `audio_processed_media_seconds` | Observed accepted chunk coverage; monotonic and never greater than total. |
| `audio_percent_complete` | Observed accepted chunk completion only; monotonic `0..100`. |
| `audio_current_chunk_index` | Observed most recently accepted chunk index. |
| `audio_total_chunks` | Observed chunk plan size after probe/normalization succeeds. |
| `audio_pipeline_percent_complete` | Measured whole-pipeline estimate; monotonic `0..100`; advances only on explicit phase transitions and accepted chunk checkpoints. |
| `audio_pipeline_eta_seconds` | Measured whole-pipeline ETA; nonnegative; updated only with explicit progress/phase timing events. |
| `phase_timings_ms` | Content-safe timing map with canonical audio phase keys plus `final_artifact_persist_ms` and `conversion_total_ms` when available. |

Use the observed `audio_*` chunk fields when presenting exact media/chunk
facts. Use `audio_pipeline_percent_complete` for a UI progress bar that should
not appear dead during `diarizing` or other long blocking phases. Use
`audio_pipeline_eta_seconds` as an estimate only; it may be `null` until there
is a measured phase basis, and it may change on later explicit phase events.

Safe stage names for normal Swedish UI copy include:

| Stage | Example Swedish copy |
| --- | --- |
| `queued` | Väntar |
| `starting` | Startar |
| `probing_media` | Läser in ljud |
| `normalizing_audio` | Förbereder ljud |
| `diarizing` | Hittar talare |
| `transcribing` | Transkriberar |
| `aligning_segments` | Synkar talare och text |
| `packaging` | Förbereder resultat |
| `succeeded` | Klar |
| `failed` | Misslyckades |
| `canceled` | Avbruten |

Failure and timeout semantics stay on the existing Service API v2 lifecycle:
failed or canceled jobs remain terminal job records, `/result` and `/artifact`
return `409 job_not_succeeded`, and no partial transcript artifacts are exposed.
Failed audio jobs retain any phase timings measured before failure. Progress
and timing telemetry must not include transcript text, utterances, speaker
display names, raw filenames as labels, media hashes as labels, signed headers,
credentials, secrets, or artifact bytes.

## PDF Page CSS Modes

ADR-0004 defines the typed PDF layout preset surface `conversion.pdf_layout`.
Task 247 adds one explicit CSS-precedence selector for PDF outputs:
`conversion.page_css_mode`.

Use the modes as follows:

- `preset_append`
  - default when omitted for PDF outputs;
  - use for quick one-off callers that want typed paper size, orientation, and
    standard margins through `conversion.pdf_layout`;
  - the service appends the generated preset stylesheet after caller CSS.
- `author_owned`
  - use for full downstream applications that provide their own page contract in
    author CSS;
  - `conversion.pdf_layout` must be omitted;
  - the service does not append any preset page stylesheet.

For internal application integrations such as Skriptoteket-owned renderers,
prefer `author_owned` so page size, margins, and label-placement CSS stay under
one renderer-owned contract.

## Preview Rendition (Contract Rule)

“Preview” is not a separate conversion engine and not a distinct output format.

- Downstream UIs create a normal v2 job producing a normal artifact (typically `output_format="pdf"`).
- Preview jobs should default to `retention.pin: false` unless the UI explicitly wants to keep the
  artifact.

## Lifecycle Contract (Create, Poll, Result, Artifact, Cancel)

Endpoints:

- `POST /v2/convert/jobs`
- `GET /v2/convert/jobs/{job_id}`
- `GET /v2/convert/jobs/{job_id}/result`
- `GET /v2/convert/jobs/{job_id}/artifact`
- `POST /v2/convert/jobs/{job_id}/cancel`

Terminal-state behavior:

- `result` and `artifact` return `202` with pending payload while job is non-terminal.
- `result` and `artifact` return `409` `job_not_succeeded` for terminal non-success states.
- `artifact` returns binary body only for `succeeded` jobs.

### Status Matrix

| Endpoint | Non-terminal | Succeeded | Failed/Canceled |
| --- | --- | --- | --- |
| `GET /v2/convert/jobs/{job_id}` | `200` job payload | `200` job payload | `200` job payload |
| `GET /v2/convert/jobs/{job_id}/result` | `202` pending payload | `200` result payload | `409 job_not_succeeded` |
| `GET /v2/convert/jobs/{job_id}/artifact` | `202` pending payload | `200` binary artifact | `409 job_not_succeeded` |
| `POST /v2/convert/jobs/{job_id}/cancel` | `202` accepted | `409 job_not_cancelable` | `200` when already canceled |

## Required API Examples

### Curated app-owned PDF boundary

- App-owned downstream PDF artifacts such as Klassrumskartan seating/grouping
  exports are not the preferred Sir Convert integration target.
- Those artifacts should render locally in the owning product.
- Sir Convert remains the downstream contract for public/general-purpose
  conversion workloads.

### 1) `pdf -> md` create job

```bash
curl -sS -X POST "${SIR_BASE_URL}/v2/convert/jobs?wait_seconds=0" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "Idempotency-Key: idem_pdf_md_001" \
  -H "X-Correlation-ID: corr_pdf_md_001" \
  -F 'file=@./paper.pdf;type=application/pdf' \
  -F 'job_spec={
    "api_version":"v2",
    "source":{"kind":"upload","filename":"paper.pdf","format":"pdf"},
    "conversion":{"output_format":"md","template":null,"css_filenames":[],"reference_docx_filename":null},
    "pdf_options":{"backend_strategy":"auto","ocr_mode":"auto","table_mode":"accurate","normalize":"strict"},
    "execution":{"acceleration_policy":"gpu_required","priority":"normal","document_timeout_seconds":1800},
    "retention":{"pin":false}
  }'
```

### 2) `docx -> md` create job

```bash
curl -sS -X POST "${SIR_BASE_URL}/v2/convert/jobs?wait_seconds=0" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "Idempotency-Key: idem_docx_md_001" \
  -H "X-Correlation-ID: corr_docx_md_001" \
  -F 'file=@./input.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document' \
  -F 'job_spec={
    "api_version":"v2",
    "source":{"kind":"upload","filename":"input.docx","format":"docx"},
    "conversion":{"output_format":"md","template":null,"css_filenames":[],"reference_docx_filename":null},
    "retention":{"pin":false}
  }'
```

### 3) `html -> md` create job with resources

```bash
curl -sS -X POST "${SIR_BASE_URL}/v2/convert/jobs?wait_seconds=0" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "Idempotency-Key: idem_html_md_001" \
  -H "X-Correlation-ID: corr_html_md_001" \
  -F 'file=@./index.html;type=text/html' \
  -F 'resources=@./resources.zip;type=application/zip' \
  -F 'job_spec={
    "api_version":"v2",
    "source":{"kind":"upload","filename":"index.html","format":"html"},
    "conversion":{"output_format":"md","template":null,"css_filenames":[],"reference_docx_filename":null},
    "retention":{"pin":false}
  }'
```

### 4) `docx -> pdf` create job (layout presets)

```bash
curl -sS -X POST "${SIR_BASE_URL}/v2/convert/jobs?wait_seconds=0" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "Idempotency-Key: idem_docx_pdf_001" \
  -H "X-Correlation-ID: corr_docx_pdf_001" \
  -F 'file=@./input.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document' \
  -F 'job_spec={
    "api_version":"v2",
    "source":{"kind":"upload","filename":"input.docx","format":"docx"},
    "conversion":{
      "output_format":"pdf",
      "css_filenames":[],
      "pdf_layout":{"paper_size":"a4","orientation":"portrait","margins_mm":12},
      "reference_docx_filename":null
    },
    "retention":{"pin":false}
  }'
```

### 5) `html -> pdf` create job

```bash
curl -sS -X POST "${SIR_BASE_URL}/v2/convert/jobs?wait_seconds=0" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "Idempotency-Key: idem_html_pdf_trusted_001" \
  -H "X-Correlation-ID: corr_html_pdf_trusted_001" \
  -F 'file=@./poster.html;type=text/html' \
  -F 'resources=@./resources.zip;type=application/zip' \
  -F 'job_spec={
    "api_version":"v2",
    "source":{"kind":"upload","filename":"poster.html","format":"html"},
    "conversion":{
      "output_format":"pdf",
      "css_filenames":["poster.css"],
      "reference_docx_filename":null
    },
    "retention":{"pin":false}
  }'
```

## Template Discovery and Selection Contract

Template discovery endpoints:

- `GET /v2/templates/docx`
- `GET /v2/templates/docx/{template_id}`
- `GET /v2/templates/docx/{template_id}/versions/{version}`

Example list call:

```bash
curl -sS "${SIR_BASE_URL}/v2/templates/docx" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "X-Correlation-ID: corr_templates_list_001"
```

Example template-selected `md -> docx` submission:

```bash
curl -sS -X POST "${SIR_BASE_URL}/v2/convert/jobs?wait_seconds=0" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "Idempotency-Key: idem_md_docx_template_001" \
  -H "X-Correlation-ID: corr_md_docx_template_001" \
  -F 'file=@./lesson.md;type=text/markdown' \
  -F 'job_spec={
    "api_version":"v2",
    "source":{"kind":"upload","filename":"lesson.md","format":"md"},
    "conversion":{"output_format":"docx","template":{"template_id":"academic-report","version":"1.0.0"},"css_filenames":[],"reference_docx_filename":null},
    "retention":{"pin":false}
  }'
```

## Idempotency Replay and Collision Contract

Replay (same key + same payload):

- response returns same `job_id`
- status code is `202` while non-terminal, `200` once terminal
- response header: `X-Idempotent-Replay: true`

Collision (same key + different payload):

- response `409`
- `error.code = "idempotency_key_reused_with_different_payload"`

## Pending and Non-success Retrieval Contract

Pending retrieval example:

```bash
curl -sS "${SIR_BASE_URL}/v2/convert/jobs/${JOB_ID}/result" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "X-Correlation-ID: corr_result_pending_001"
```

Expected pending payload (`202`):

```json
{
  "api_version": "v2",
  "job_id": "jobv2_...",
  "status": "queued"
}
```

Terminal non-success retrieval (`409`):

```json
{
  "api_version": "v2",
  "error": {
    "code": "job_not_succeeded",
    "message": "Job is terminal but has no successful conversion result.",
    "retryable": false,
    "details": {
      "status": "failed"
    },
    "correlation_id": "corr_..."
  }
}
```

## CLI Parity Contract (for GUI Tooling + Operator UX)

Route discovery must match service route taxonomy:

```bash
pdm run convert-a-lot routes
```

Dry-run route resolution examples:

```bash
pdm run convert-a-lot convert ./template.docx --to md --output-dir ./out --dry-run
pdm run convert-a-lot convert ./index.html --to md --output-dir ./out --dry-run
```

Manifest entry shape includes deterministic route metadata:

```json
{
  "source_file_path": "doc.html",
  "job_id": "job_ok_doc",
  "status": "succeeded",
  "output_path": "/abs/path/out/doc.pdf",
  "error_code": null,
  "source_format": "html",
  "target_format": "pdf",
  "pipeline_used": "service: html -> pdf (v2)"
}
```

## Adapter Integration Patterns

### Skriptoteket/HuleEdu (thin adapter path)

Use `scripts/sir_convert_a_lot/integrations/adapter_profiles.py`:

- `prepare_submission(...)` for deterministic `Idempotency-Key` + `X-Correlation-ID`
- `submit_pdf_for_profile(...)` for canonical v2 submit/poll/download flow

Adapter invariants:

- canonical v2 `job_spec` shape
- deterministic idempotency derivation from payload + file bytes
- caller correlation id pass-through when supplied

### Projektveckor (backend HTTP path)

Projektveckor should call the same v2 endpoints directly with the same invariants:

- route set and lifecycle semantics are identical to Skriptoteket/HuleEdu
- send canonical headers (`X-API-Key`, `Idempotency-Key`, `X-Correlation-ID`)
- use mirrored secret policy from ops runbook:
  - `PVP_SIR_CONVERT_A_LOT_V2_API_KEY` must equal `SIR_CONVERT_A_LOT_V2_API_KEY`

Minimal request pattern (Python/httpx):

```python
import json
import os
from pathlib import Path

import httpx

base_url = os.environ["SIR_BASE_URL"].rstrip("/")
api_key = os.environ["PVP_SIR_CONVERT_A_LOT_V2_API_KEY"]
source = Path("paper.pdf")

spec = {
    "api_version": "v2",
    "source": {"kind": "upload", "filename": source.name, "format": "pdf"},
    "conversion": {
        "output_format": "md",
        "template": None,
        "css_filenames": [],
        "reference_docx_filename": None,
    },
    "pdf_options": {
        "backend_strategy": "auto",
        "ocr_mode": "auto",
        "table_mode": "accurate",
        "normalize": "strict",
    },
    "execution": {
        "acceleration_policy": "gpu_required",
        "priority": "normal",
        "document_timeout_seconds": 1800,
    },
    "retention": {"pin": False},
}

with httpx.Client(base_url=base_url, timeout=60.0) as client:
    with source.open("rb") as handle:
        response = client.post(
            "/v2/convert/jobs",
            params={"wait_seconds": 0},
            headers={
                "X-API-Key": api_key,
                "Idempotency-Key": "idem_projectveckor_001",
                "X-Correlation-ID": "corr_projectveckor_001",
            },
            data={"job_spec": json.dumps(spec, separators=(",", ":"), sort_keys=True)},
            files={"file": (source.name, handle, "application/pdf")},
        )
    response.raise_for_status()
```

## Deterministic Error Contract (Selected Codes)

| Scenario | Status | Error code |
| --- | --- | --- |
| Missing/invalid API key | `401` | `auth_invalid_api_key` |
| Missing `Idempotency-Key` | `400` | `idempotency_key_missing` |
| Reused key with different payload | `409` | `idempotency_key_reused_with_different_payload` |
| Unsupported file type | `415` | `unsupported_media_type` |
| Empty upload | `422` | `input_unreadable` |
| Pending result/artifact | `202` | pending payload (not error envelope) |
| Terminal non-success result/artifact | `409` | `job_not_succeeded` |
| Unknown template id/version in create request | `422` | `validation_error` |
| Disabled template selection | `409` | `template_unavailable` |

## Evidence Matrix (Normative Statement -> Source and Tests)

| Contract area | Primary sources | Validation tests |
| --- | --- | --- |
| v2 lifecycle endpoints and status semantics | `docs/converters/multi_format_conversion_service_api_v2.md`, `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py` | `tests/sir_convert_a_lot/test_api_contract_v2.py`, `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_read_cancel.py` |
| `pdf -> md` v2 lock and v1 absence | `scripts/sir_convert_a_lot/interfaces/http_api.py`, `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py` | `tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py` |
| `docx -> md` route | `scripts/sir_convert_a_lot/domain/specs_v2.py`, `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py` | `tests/sir_convert_a_lot/test_api_contract_v2_docx_to_md.py` |
| `html -> md` route + resources policy | `scripts/sir_convert_a_lot/interfaces/http_jobs_v2_request_validation.py` | `tests/sir_convert_a_lot/test_api_contract_v2_html_to_md.py`, `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py` |
| Template discovery endpoints | `scripts/sir_convert_a_lot/interfaces/http_routes_templates_v2.py`, `docs/converters/docx-template-catalog-contract-v2.md` | `tests/sir_convert_a_lot/test_http_routes_templates_v2.py` |
| Template selector validation | `scripts/sir_convert_a_lot/interfaces/http_jobs_v2_request_validation.py` | `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_templates.py`, `tests/sir_convert_a_lot/test_api_contract_v2_docx_templates.py` |
| CLI route/dry-run parity + manifest fields | `docs/converters/sir_convert_a_lot.md`, `scripts/sir_convert_a_lot/interfaces/cli_routes.py`, `scripts/sir_convert_a_lot/interfaces/cli_app.py` | `tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py`, `tests/sir_convert_a_lot/test_cli_v2_routes.py` |
| Adapter profile behavior (Skriptoteket/HuleEdu) | `scripts/sir_convert_a_lot/integrations/adapter_profiles.py` | `tests/sir_convert_a_lot/test_integration_adapter_conformance.py` |
| Projektveckor secret mirroring policy | `docs/runbooks/runbook-hemma-devops-and-gpu.md` | Operational policy evidence in Task 43 docs: `docs/backlog/tasks/task-43-publish-convert-domain-and-centralize-prod-env-mirroring-across-internal-repos.md` |
