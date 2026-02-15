---
id: task-20-harden-markdown-normalization-for-math-artifacts-and-docling-export-escaping
title: Harden markdown normalization for math artifacts and Docling export escaping
type: task
status: in_progress
priority: high
created: '2026-02-15'
last_updated: '2026-02-15'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-10-docling-backend-ocr-policy-mapping-deterministic-markdown-normalization-width-100.md
  - docs/backlog/tasks/task-18-root-cause-fix-deterministic-service-execution-and-artifact-integrity.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - markdown
  - docling
  - quality
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Eliminate deterministic markdown artifact regressions in the production conversion
surface by hardening strict normalization for math-heavy output and reducing
escaped HTML symbol noise from Docling export.

## PR Scope

- Protect math blocks from strict prose reflow to avoid breaking equations.
- Add bounded cleanup for pathological slash-padding lines generated inside math
  blocks.
- Export Docling markdown without forced HTML-escaped symbols where supported.
- Add targeted regression tests for normalizer and backend export behavior.
- Validate with canonical CLI against the three worst PDFs and persist output under
  `build/manual-validation-quality-control`.

## Deliverables

- [ ] Math-aware strict normalizer update in
  `scripts/sir_convert_a_lot/infrastructure/markdown_normalizer.py`
- [ ] Docling export-escaping hardening in
  `scripts/sir_convert_a_lot/infrastructure/docling_backend.py`
- [ ] Regression tests updated in `tests/sir_convert_a_lot/`
- [ ] Production-surface CLI evidence for three hard PDFs in `build/`

## Acceptance Criteria

- [ ] Strict normalization no longer reflows content inside display-math blocks.
- [ ] Long pathological `\ \ \` padding runs are removed only in math-safe context.
- [ ] HTML entity noise (`&lt;`, `&gt;`) is reduced via backend export settings.
- [ ] Targeted local tests pass and canonical CLI conversion succeeds for all three
  hard PDFs.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
