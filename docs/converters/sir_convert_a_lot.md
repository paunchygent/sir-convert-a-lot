---
type: converter
id: CONV-sir-convert-a-lot
title: Sir Convert-a-Lot CLI and Service Usage
status: active
created: '2026-02-11'
updated: '2026-02-16'
owners:
  - platform
tags:
  - cli
  - usage
  - tunnel
links:
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
---

## Purpose

`Sir Convert-a-Lot` is the canonical local client for submitting conversion jobs to the
Hemma-hosted conversion service over internal HTTP/tunnel.

Natural-language usage convention for assistants:

- `Please, tell Sir Convert-a-Lot to convert x to y.`
- `Please, tell convert-a-lot to convert x to y.`

In v1, `x` must be PDF input and `y` is Markdown (`md`).

## Service Contract

- Normative API: `docs/converters/pdf_to_md_service_api_v1.md`
- Decision lock: `docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md`

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
  - HTTP client adapter (`http_client.py`)
  - CLI adapter (`cli_app.py`)
- Compatibility facades at package root (`service.py`, `client.py`, `cli.py`, `models.py`, `runtime.py`)
  preserve stable imports during migration.

## Local Commands

Run service locally:

```bash
pdm run serve:sir-convert-a-lot
```

Run conversion client:

```bash
pdm run convert-a-lot convert ./pdfs --output-dir ./research
```

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

## Tunnel-Oriented Development Flow

1. Start service on Hemma (or locally for testing).
1. Expose the service through your local tunnel endpoint.
1. Run from any repo directory:

```bash
pdm run convert-a-lot convert ./folder_with_pdfs \
  --output-dir ./research \
  --service-url http://127.0.0.1:18085 \
  --api-key "$SIR_CONVERT_A_LOT_API_KEY" \
  --backend-strategy auto \
  --ocr-mode auto \
  --table-mode accurate \
  --normalize strict \
  --acceleration-policy gpu_required
```

## Deterministic Manifest

Each batch writes `sir_convert_a_lot_manifest.json` in `--output-dir` with entries containing:

- `source_file_path`
- `job_id`
- `status`
- `output_path`
- `error_code`

This manifest is the canonical audit artifact for assistant-driven batch conversions.

Long-running note:

- If `--max-poll-seconds` is exceeded, CLI records the entry as `status: running` with `job_id`
  and `error_code: job_timeout` instead of marking it as failed.
- Conversion continues server-side; callers can query:
  - `GET /v1/convert/jobs/{job_id}`
  - `GET /v1/convert/jobs/{job_id}/result`
