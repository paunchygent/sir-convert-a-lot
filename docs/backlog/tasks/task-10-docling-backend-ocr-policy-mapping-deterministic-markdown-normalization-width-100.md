---
id: task-10-docling-backend-ocr-policy-mapping-deterministic-markdown-normalization-width-100
title: 'Docling backend: OCR policy mapping + deterministic markdown normalization (width=100)'
type: task
status: proposed
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

- [ ] Docling backend implementation behind canonical v1 job spec fields.
- [ ] Deterministic Markdown normalization layer (width 100 strict strong-reflow).
- [ ] Unit tests covering normalization safety (fences/tables/headings/lists) and determinism.
- [ ] Updated converter API docs defining normalization semantics and line-break guarantees.

## Acceptance Criteria

- [ ] For the same input PDF + identical job spec:
  - output Markdown is byte-identical across repeated runs.
- [ ] `conversion.normalize="strict"` enforces width 100 strong reflow on prose blocks and does not
  reflow fenced code blocks or Markdown tables.
- [ ] OCR mode behaviors match spec and are deterministic.
- [ ] Successful results always include mandatory metadata fields (backend/acceleration/options fingerprint).
- [ ] Quality gates pass (format/lint/typecheck/tests + docs validators and backlog index).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
