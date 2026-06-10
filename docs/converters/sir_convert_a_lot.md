---
type: converter
id: CONV-sir-convert-a-lot
title: Sir Convert-a-Lot CLI and Service Usage
status: active
created: '2026-02-11'
updated: '2026-03-06'
owners:
  - platform
tags:
  - cli
  - usage
  - tunnel
links:
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
---

## Purpose

`Sir Convert-a-Lot` is the canonical client for submitting conversion jobs to the
Hemma-hosted conversion service over:

- tunnel lane: `http://127.0.0.1:28085`
- Gateway/public lane: disabled until the Gateway cutover deliberately
  re-enables the intended public edge

Natural-language usage convention for assistants:

- `Please, tell Sir Convert-a-Lot to convert x to y.`
- `Please, tell convert-a-lot to convert x to y.`

Service API v2 is the conversion surface for **multi-format** conversions executed on Hemma
(dockerized runtime). The CLI is a thin submit/poll/download wrapper and does not require
Pandoc/WeasyPrint to be installed on the caller machine.

The CLI exposes a typed route registry for supported/planned conversions. Routes include:

- `pdf -> md` (service v2)
- `docx -> md` (service v2)
- `html -> md` (service v2)
- `pdf -> docx` (service v2 pipeline)
- `html + css -> pdf` (service v2)
- `html -> docx` (service v2)
- `md -> html -> pdf` (service v2)
- `md -> html -> docx` (service v2)
- approved next route: `md -> wav` (Hemma sidecar TTS; not yet implemented)

Planned routes remain discoverable via `convert-a-lot routes` and `--dry-run`.

## Service V2 Route Boundary

`POST /v2/convert/jobs` resolves supported routes through
`domain.service_routes_v2` and `interfaces.http_create_job_routes_v2`.
`domain.service_routes_v2` owns the shared route-policy metadata consumed by
`JobSpecV2` validation and HTTP create-job handler lookup. The generic job
endpoint owns multipart mechanics, auth context, idempotency, route lookup, and
job persistence; route handlers own route-specific companion uploads and target
preparation.

The `examnet_artifact -> teacher_authoring_bundle` route remains draft-only
until a later governed runtime task registers and implements that route.

## Local Runtime Rule

For local app integration and local verification that depends on the `:8085`
service lane:

- start Sir Convert-a-Lot with `pdm run dev-start`
- inspect it with `pdm run dev-logs`
- never use `pdm run serve:sir-convert-a-lot`
- never start `uvicorn scripts.sir_convert_a_lot.service:app` directly

Rationale: the supported local `:8085` lane is an explicit CPU-only Docker dev
service, not a host-run Python process and not the Hemma ROCm production image.
That keeps laptop debugging deterministic while the real integration path stays
on Hemma through the tunnel/internal lane until the Gateway-fronted public lane
is proven and explicitly re-enabled.

TTS planning note:

- TTS is planned as a sidecar-backed Hemma service route, not a laptop-local auxiliary command.
- The first approved route is `md -> wav`.
- `pdf -> wav` is deferred until the sidecar-backed `md -> wav` contract is implemented.

## Idempotency and Reruns (CLI UX)

Service API v2 requires `Idempotency-Key` for `POST /v2/convert/jobs`. The CLI generates a
deterministic key for safety (double-clicks/retries do not spawn duplicate jobs).

User-facing rerun behavior:

- Default: if the server returns an idempotent replay and the replayed job is terminal `failed` or
  `canceled`, the CLI automatically submits a new job once (no filename hacks required).
- `--replay-only`: disable the auto-rerun behavior and keep strict replay semantics.
- `--new-job`: always submit with a new `Idempotency-Key`, even if a prior job succeeded.

## Service Contract

- Normative API: `docs/converters/multi_format_conversion_service_api_v2.md`
- Downstream integration contract:
  `docs/converters/downstream_integration_contract_v2.md`
- Decision v2:
  `docs/decisions/0012-service-api-v2-current-state-authority-and-extension-boundary.md`

## Task 11 Backend Availability

- Docling path:
  - `conversion.backend_strategy="auto"` (Docling-first routing)
  - `conversion.backend_strategy="docling"`
- PyMuPDF path:
  - `conversion.backend_strategy="pymupdf"` is available with strict compatibility rules:
    - `conversion.ocr_mode` must be `off`
    - `execution.acceleration_policy` must be CPU-compatible (`cpu_only`)

Deterministic validation behavior:

- `pymupdf` + `acceleration_policy in {"gpu_required","gpu_prefer"}` ->
  - `422 validation_error`
  - details:
    `{"field":"conversion.backend_strategy","reason":"backend_incompatible_with_gpu_policy"}`
- `pymupdf` + `ocr_mode in {"auto","force"}` ->
  - `422 validation_error`
  - details:
    `{"field":"conversion.ocr_mode","reason":"backend_option_incompatible","backend":"pymupdf","supported":["off"]}`

## GPU Runtime Compliance Gate

For GPU-governed Docling execution, runtime now fails closed when a usable GPU runtime
is unavailable for the backend.

Docling is GPU-only by invariant in all paths:

- service runtime execution,
- direct backend execution,
- tests and harnesses.

Deterministic failure path:

- `503 gpu_not_available`
- `error.details.reason = "backend_gpu_runtime_unavailable"`
- details include `backend`, `runtime_kind`, `hip_version`, `cuda_version`.

Hemma verification/remediation commands:

```bash
pdm run run-local-pdm hemma-verify-gpu-runtime
pdm run run-local-pdm hemma-repair-rocm-runtime
```

`acceleration_used` remains normalized as `"cuda"` for successful GPU execution, including ROCm.

## OCR and Normalization Semantics

- OCR mode mapping:
  - `off`: single pass with OCR disabled.
  - `force`: single pass with OCR enabled + full-page OCR forced.
  - `auto`: deterministic pass-1 without OCR, followed by one OCR retry only when:
    - markdown is empty, or
    - chars/page is below `120`, or
    - confidence low-grade is `poor`/`fair` (when confidence is available).
- OCR engine + language selection (PDF routes; service API v2):
  - `--ocr-engine auto|easyocr|tesseract_cli` (default: `auto` delegates to runtime defaults)
  - `--ocr-language <tag>` (repeatable; BCP47/ISO639-1 tags like `sv`, `en`, `sv-SE`)
  - Result metadata reports `ocr_enabled`, `ocr_engine_used`, and
    `ocr_languages_used` only.
  - Requested OCR languages remain request input (`pdf_options.ocr_languages`);
    `ocr_acceleration_used` is deferred until OCR-stage acceleration is observed
    separately from backend `acceleration_used`.
  - Hemma runtime defaults are controlled by env vars:
    - `SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE`
    - `SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES` (comma-separated, e.g. `sv,en`)
    - `SIR_CONVERT_A_LOT_EASYOCR_MODEL_STORAGE_DIR` (must exist when EasyOCR downloads are disabled)
  - Missing engine/language is rejected at v2 job creation (preflight) to prevent multi-hour
    wrong-OCR runs.
- Markdown normalization:
  - `none`: preserve backend output.
  - `standard`: deterministic whitespace/blank-line cleanup.
  - `strict`: strong prose reflow to width `100` while preserving markdown structure
    (no reflow in fences/tables/headings/lists/quotes/horizontal rules).

## DDD-Oriented Package Layout

`scripts/sir_convert_a_lot/` is structured for long-term evolution:

- `domain/`
  - Core conversion job language and invariants (`specs.py`).
- `application/`
  - Shared response/manifest contracts (`contracts.py`).
- `infrastructure/`
  - Filesystem-backed runtime engine (`runtime_engine.py`).
- `interfaces/`
  - HTTP API adapter (`http_api.py`)
  - HTTP client adapter (`http_client_v2.py`)
  - CLI adapter (`cli_app.py`)
- Package-root service entrypoints are limited to current files such as
  `service.py` and `service_local.py`; client and model imports should use the
  current `interfaces/`, `application/`, `domain/`, and `infrastructure/`
  modules directly.

## Client Commands

Run conversion client:

```bash
pdm run convert-a-lot convert ./pdfs --output-dir ./research
```

List supported (implemented + planned) routes:

```bash
pdm run convert-a-lot routes
```

Preview route selection and pipeline steps without executing:

```bash
pdm run convert-a-lot convert ./pdfs --output-dir ./research --dry-run --to md
```

Convert DOCX to Markdown via the service (v2):

```bash
pdm run convert-a-lot convert ./template.docx \
  --to md \
  --output-dir ./out \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY"
```

Convert HTML to Markdown via the service (v2), with optional resources:

```bash
pdm run convert-a-lot convert ./index.html \
  --to md \
  --resources ./assets \
  --output-dir ./out \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY"
```

Convert HTML (+ optional CSS) to PDF via the service (v2):

```bash
pdm run convert-a-lot convert ./handout.html \
  --to pdf \
  --output-dir ./out \
  --css ./styles/handout.css \
  --resources ./styles \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY"
```

Resources note:

- Use `--resources <dir-or-zip>` to upload images/fonts/CSS referenced by HTML/Markdown.
- When `--css` is used for PDF outputs, the CLI ensures the CSS is present in the uploaded v2 resources
  bundle and references it via `conversion.css_filenames`.

Convert Markdown to PDF via an HTML intermediary (service v2 pipeline):

```bash
pdm run convert-a-lot convert ./notes.md \
  --to pdf \
  --output-dir ./out \
  --resources ./assets \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY"
```

Title handling (deterministic):

- Uses YAML frontmatter `title` when present.
- Otherwise uses the first Markdown H1 (`# ...`) if present.
- Otherwise uses the filename stem.

Convert Markdown to DOCX via an HTML intermediary (service v2 pipeline):

```bash
pdm run convert-a-lot convert ./notes.md \
  --to docx \
  --output-dir ./out \
  --resources ./assets \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY"
```

Title handling uses the same deterministic rules as MD→PDF (frontmatter `title`, first H1, stem).

Optional styling via a reference DOCX:

```bash
pdm run convert-a-lot convert ./notes.md \
  --to docx \
  --output-dir ./out \
  --reference-docx ./reference.docx \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY"
```

Convert PDF to DOCX via the service v2 pipeline:

```bash
pdm run convert-a-lot convert ./paper.pdf \
  --to docx \
  --output-dir ./out \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY"
```

`pdf -> docx` is delivered by the explicit service API v2 surface.

Optional styling via a reference DOCX is supported for this service v2 route as well:

```bash
pdm run convert-a-lot convert ./paper.pdf \
  --to docx \
  --output-dir ./out \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY" \
  --reference-docx ./reference.docx
```

Timeout behavior:

- If `--max-poll-seconds` is exceeded but the job remains active (fresh heartbeat/progress), the
  manifest entry remains `status: running` with `job_id` and `error_code: job_poll_window_exceeded`.
- If the job appears stalled (stale heartbeat/progress beyond `--stall-timeout-seconds`), the
  manifest entry remains `status: running` with `job_id` and `error_code: job_timeout`, and the CLI
  exits non-zero to force operator attention.

Directory disambiguation note:

- When converting a directory, multiple input formats may be present for the selected target.
- For `--to md`, `pdf`, `docx`, and `html` are valid source formats; use `--from` to disambiguate.
- For non-`md` targets, use `--from` to disambiguate (for example `--from md` or `--from html`).

Docker lane note:

- WeasyPrint requires native libraries and Pandoc requires an OS package.
  The runtime image installs Debian packages:
  `libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz-subset0`, and `pandoc`.

Default CLI submission profile is production-quality:

- `conversion.backend_strategy=auto`
- `conversion.ocr_mode=auto`
- `conversion.table_mode=accurate`
- `conversion.normalize=strict`
- `execution.acceleration_policy=gpu_required`

Docling default layout profile is quality-first:

- service default layout model: `docling_layout_egret_large`
- optional override env var: `SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL`
- supported override values:
  - `docling_layout_v2`
  - `docling_layout_heron`
  - `docling_layout_heron_101`
  - `docling_layout_egret_medium`
  - `docling_layout_egret_large`
  - `docling_layout_egret_xlarge`

Alias command (same behavior):

```bash
pdm run sir-convert-a-lot convert ./pdfs --output-dir ./research
```

## Canonical Access Flow

1. Ensure service is running on Hemma.
1. Choose exactly one client lane:
   - tunnel: `http://127.0.0.1:28085`
   - Gateway/public lane: disabled until cutover proof re-enables it
1. Run from any repo directory:

```bash
pdm run convert-a-lot convert ./folder_with_pdfs \
  --output-dir ./research \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY" \
  --backend-strategy auto \
  --ocr-mode auto \
  --ocr-engine auto \
  --table-mode accurate \
  --normalize strict \
  --acceleration-policy gpu_required
```

Force Swedish OCR with explicit engine/languages:

```bash
pdm run convert-a-lot convert ./folder_with_pdfs \
  --output-dir ./research \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY" \
  --ocr-mode force \
  --ocr-engine easyocr \
  --ocr-language sv \
  --ocr-language en
```

The direct internet lane is disabled before the Gateway cutover. Use the tunnel
lane for operator conversion work until a Gateway-fronted public path is proven
and explicitly re-enabled.

```bash
curl -isS https://convert.hule.education/readyz
```

## Deterministic Manifest

Each batch writes `sir_convert_a_lot_manifest.json` in `--output-dir` with entries containing:

- `source_file_path`
- `source_format`
- `target_format`
- `pipeline_used`
- `job_id`
- `status`
- `output_path`
- `error_code`

This manifest is the canonical audit artifact for assistant-driven batch conversions.

Long-running note:

- During service-backed v2 runs, the CLI updates this manifest incrementally
  once a job id is observed. A local interruption after submission should leave
  a valid manifest entry with the known `job_id`, non-terminal `status`, and an
  interruption/error code instead of an empty output directory.
- Submitted and idempotent-replay jobs are printed as explicit operator lines
  before terminal artifact download, so a reused running job is not mistaken for
  a duplicate fresh submission or a silent stall.
- If `--max-poll-seconds` is exceeded, CLI records the entry as `status: running` with `job_id` and
  `error_code: job_poll_window_exceeded` instead of marking it as failed.
- Conversion continues server-side; callers can query:
  - v2 multi-format:
    - `GET /v2/convert/jobs/{job_id}`
    - `GET /v2/convert/jobs/{job_id}/result`
    - `GET /v2/convert/jobs/{job_id}/artifact`
