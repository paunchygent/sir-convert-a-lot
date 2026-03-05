---
id: 'story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness'
title: 'GPU-accelerated multilingual OCR engine selection and Swedish diacritics correctness'
type: 'story'
status: 'proposed'
priority: 'high'
created: '2026-03-05'
last_updated: '2026-03-05'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - Dockerfile
  - scripts/sir_convert_a_lot/domain/specs_v2.py
  - scripts/sir_convert_a_lot/infrastructure/conversion_backend.py
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
  - scripts/sir_convert_a_lot/interfaces/cli_app.py
  - scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py
labels:
  - ocr
  - multilingual
  - swedish
  - performance
  - gpu
  - hemma
---
Implementation slice with acceptance-driven scope.

## Objective

Make PDF OCR both correct for Swedish (preserve `å`, `ä`, `ö`) and fast enough for large batches by:

- selecting a GPU-capable OCR engine by default (EasyOCR on Hemma),
- providing a deterministic offline alternative (Tesseract + Swedish language data),
- failing fast on engine/language drift to avoid multi-hour wrong-output runs,
- adding deploy-time live verification that catches diacritics regressions.

## Scope

- Contract and CLI surface:
  - Extend v2 PDF options with explicit OCR engine + language selection.
  - Expose the same controls in the CLI (`convert-a-lot convert`).
  - Emit `ocr_engine_used` + `ocr_languages_used` in `result.conversion_metadata` for auditability.
- Runtime implementation:
  - Default OCR engine on Hemma: EasyOCR with GPU enabled and Swedish+English languages.
  - Optional OCR engine: Tesseract (CLI) with Swedish+English language packs.
  - No silent fallback when an engine/language is explicitly requested.
- Preflight gates:
  - Reject conversions immediately when requested OCR engine/language is unavailable.
  - Reject “GPU-required” OCR requests when OCR engine cannot run with GPU.
- Deploy-time verification:
  - Add a lightweight Swedish OCR smoke step to the existing Hemma live verification flow.
  - Capture deterministic evidence artifacts (readyz/metrics/result payload + small OCR artifact excerpt).
- Performance evidence:
  - Define a benchmark harness invocation and target metric thresholds for batch OCR throughput.
  - Require a Hemma live run that records throughput metrics and stage timings.

## Acceptance Criteria

- [ ] Swedish OCR correctness is guaranteed for the deploy-time smoke fixture(s):
  - output contains `å`, `ä`, `ö`,
  - `result.conversion_metadata.ocr_enabled=true`.
- [ ] OCR engine + language selection are explicit and observable:
  - v2 accepts engine/language fields in PDF options,
  - `result.conversion_metadata` includes `ocr_engine_used` + `ocr_languages_used`.
- [ ] Default Hemma OCR engine is GPU-capable and verified live:
  - EasyOCR is the default for OCR-enabled PDF runs,
  - `acceleration_used="cuda"` and no CPU fallback warning for GPU-required jobs.
- [ ] Preflight is fail-fast and actionable:
  - missing engine/language fails at job creation (no multi-hour run),
  - error message includes remediation steps (install/enable engine + language).
- [ ] Deploy-time verification includes Swedish OCR smoke and metrics safety checks:
  - `/readyz` is green and revision-parity checked,
  - `/metrics` contains no high-cardinality labels (`job_id` etc),
  - smoke report artifacts are written under a deterministic `build/verification/...` directory.
- [ ] Performance target (Hemma live evidence):
  - batch throughput improves materially versus the documented baseline,
  - explicit target for the operator-provided “300 PDFs” corpus:
    - total wall-clock <= 60 minutes on Hemma default tuned profile,
    - evidence includes median `pages_per_minute` and stage timings.

## Test Requirements

- [ ] Contract tests:
  - v2 request validation for OCR engine + language fields,
  - conversion metadata includes `ocr_engine_used` and languages.
- [ ] Preflight tests:
  - missing Tesseract language pack rejects immediately,
  - missing EasyOCR dependency/model rejects immediately.
- [ ] Swedish diacritics regression:
  - minimal OCR fixture conversion asserts output includes `åäö`.

## Done Definition

Operators can run large OCR batches with:

- correct Swedish text output (no diacritics loss),
- explicit engine/language selection (default EasyOCR on Hemma, optional Tesseract),
- deterministic preflight failures that prevent wasted multi-hour runs,
- deploy-time smoke coverage + recorded evidence artifacts.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
