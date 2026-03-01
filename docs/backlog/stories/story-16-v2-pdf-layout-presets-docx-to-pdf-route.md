---
id: story-16-v2-pdf-layout-presets-docx-to-pdf-route
title: V2 PDF layout presets + DOCX to PDF route
type: story
status: proposed
priority: high
created: '2026-03-01'
last_updated: '2026-03-01'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/decisions/0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/backlog/tasks/task-64-adr-0004-v2-pdf-layout-presets-preview-docx-to-pdf.md
  - docs/backlog/tasks/task-65-add-v2-pdf-layout-presets-paper-orientation-for-pdf-outputs.md
  - docs/backlog/tasks/task-66-add-v2-route-docx-to-pdf-via-pandoc-html-and-weasyprint.md
labels:
  - v2
  - pdf
  - docx
  - presets
  - downstream
---

Implementation slice with acceptance-driven scope.

## Objective

Define and ship the missing v2 conversion contract + runtime slices needed for downstream GUI
products to treat Sir Convert-a-Lot as the single canonical PDF artifact engine for:

- `html -> pdf`
- `md -> pdf`
- `docx -> pdf`

This includes a typed PDF layout preset surface (paper + orientation + margins) so downstream
products do not build a “CSS-as-API” shadow contract.

## Scope

In scope:

- ADR-0004 decision and contract alignment.
- v2 JobSpec extension for PDF layout presets (PDF-only).
- Runtime support for applying presets to all PDF-output routes.
- Add v2 `docx -> pdf` route implemented as `docx -> html (pandoc) -> pdf (weasyprint)`.
- Normative docs updates for the v2 API and downstream integration contract.

Out of scope:

- Batch conversion semantics (belongs to downstream orchestrators, not the service contract).
- A distinct “preview output format”; preview is a normal PDF job producing a normal PDF artifact.

## Acceptance Criteria

- [ ] ADR-0004 is accepted and linked from normative converter docs.
- [ ] v2 supports `conversion.pdf_layout` for PDF outputs with deterministic validation errors.
- [ ] v2 supports `docx -> pdf` as an allowed route with deterministic pipeline naming.
- [ ] All new/changed behavior is covered by contract + unit tests, and `pdm run run-local-pdm coverage-gate`
  remains >= 90%.

## Test Requirements

- [ ] Contract tests cover:
  - `conversion.pdf_layout` validation rules and defaults.
  - `docx -> pdf` route acceptance and output artifact content type.
- [ ] Executor tests cover:
  - preset stylesheet generation is applied for `html -> pdf` and `md -> pdf` (and `docx -> pdf` once added).
  - deterministic `422` mapping for missing CSS/resource or unreadable DOCX.

## Done Definition

This story is done when the tasks below are terminalized in strict order and the v2 docs surface is
explicit enough for downstream GUIs to implement a complete conversion UI without inventing a
separate conversion engine.

## Task Order (Strict)

- [x] `docs/backlog/tasks/task-64-adr-0004-v2-pdf-layout-presets-preview-docx-to-pdf.md`
- [x] `docs/backlog/tasks/task-65-add-v2-pdf-layout-presets-paper-orientation-for-pdf-outputs.md`
- [ ] `docs/backlog/tasks/task-66-add-v2-route-docx-to-pdf-via-pandoc-html-and-weasyprint.md`

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
