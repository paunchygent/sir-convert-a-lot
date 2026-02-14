---
id: task-10-docling-backend-ocr-policy-mapping-deterministic-markdown-normalization-width-100
title: 'Docling backend: OCR policy mapping + deterministic markdown normalization (width=100)'
type: task
status: completed
priority: critical
created: '2026-02-14'
last_updated: '2026-02-14'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - .agents/rules/035-docling-pdf-conversion.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine.py
labels:
  - docling
  - pdf-to-md
  - normalization
  - ocr
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement a production-grade Docling conversion backend that honors v1 job spec fields and produces
deterministically normalized Markdown with readable, Markdown-best-practice line breaks.

## PR Scope

- Add pinned Docling dependency and wire backend selection via `conversion.backend_strategy`.
- Implement OCR mapping for `conversion.ocr_mode`:
  - `off`: OCR disabled
  - `force`: OCR enabled
  - `auto`: first pass without OCR; deterministic OCR retry based on content-length/page heuristic
- Implement deterministic Markdown normalization:
  - `normalize=standard`: safe whitespace normalization (no aggressive reflow)
  - `normalize=strict`: strong paragraph reflow to width 100, while preserving Markdown structure
- Ensure conversion metadata truth:
  - `conversion_metadata.backend_used="docling"`
  - `conversion_metadata.acceleration_used` reflects actual device availability.

## Deliverables

- [x] Docling backend implementation behind canonical v1 job spec fields.
- [x] Deterministic Markdown normalization layer (width 100 strict strong-reflow).
- [x] Unit tests covering normalization safety (fences/tables/headings/lists) and determinism.
- [x] Updated converter API docs defining normalization semantics and line-break guarantees.

## Acceptance Criteria

- [x] For the same input PDF + identical job spec:
  - output Markdown is byte-identical across repeated runs.
- [x] `conversion.normalize="strict"` enforces width 100 strong reflow on prose blocks and does not
  reflow fenced code blocks or Markdown tables.
- [x] OCR mode behaviors match spec and are deterministic.
- [x] Successful results always include mandatory metadata fields (backend/acceleration/options fingerprint).
- [x] Quality gates pass (format/lint/typecheck/tests + docs validators and backlog index).

## Execution Plan

1. Add exact Docling dependency pin and synchronize lockfile.
1. Introduce conversion backend seam + Docling backend implementation:
   - `conversion_backend.py`
   - `docling_backend.py`
1. Introduce deterministic Markdown normalization module:
   - `markdown_normalizer.py`
1. Refactor runtime to delegate conversion and normalization through the new seam.
1. Enforce temporary backend availability rule:
   - reject `backend_strategy="pymupdf"` with `422 validation_error` and stable `details`.
1. Add/adjust tests with real PDF fixtures for conversion-success paths.
1. Update converter/API docs and close out task + session docs after validation gates pass.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
