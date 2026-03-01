---
id: 'task-65-add-v2-pdf-layout-presets-paper-orientation-for-pdf-outputs'
title: 'Add v2 PDF layout presets (paper/orientation) for PDF outputs'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-01'
last_updated: '2026-03-01'
related:
  - docs/backlog/stories/story-16-v2-pdf-layout-presets-docx-to-pdf-route.md
  - docs/backlog/tasks/task-64-adr-0004-v2-pdf-layout-presets-preview-docx-to-pdf.md
  - docs/decisions/0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md
  - scripts/sir_convert_a_lot/domain/specs_v2.py
  - scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - v2
  - pdf
  - contract
  - executor
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add a typed, PDF-only layout preset surface to v2 jobs so downstream products can request standard
page setups without shipping ad hoc CSS conventions.

## PR Scope

Implement `conversion.pdf_layout` and apply it to all PDF-output routes:

- `html -> pdf`
- `md -> pdf`
- (and `docx -> pdf` once Task 66 lands)

Implementation must:

- remain deterministic and typed (no raw CSS injection),
- remain workdir-bounded and compatible with WeasyPrint sandboxing,
- preserve existing `conversion.css_filenames` support for content styling.

## Deliverables

- [ ] v2 JobSpec supports `conversion.pdf_layout` (PDF outputs only) with deterministic validation errors.
- [ ] Executor generates and applies a deterministic preset stylesheet for PDF outputs.
- [ ] `docs/converters/multi_format_conversion_service_api_v2.md` updated with schema + examples.
- [ ] `docs/converters/downstream_integration_contract_v2.md` updated with schema + examples.
- [ ] Spec validation tests cover `conversion.pdf_layout` rules and defaults.
- [ ] Executor tests cover preset stylesheet generation and application.

## Acceptance Criteria

- [ ] A v2 job with `conversion.output_format == "pdf"` may include `conversion.pdf_layout` and is accepted.
- [ ] A v2 job with a non-PDF output rejects `conversion.pdf_layout` with a deterministic validation error.
- [ ] Preset application is deterministic and does not depend on caller-provided CSS.
- [ ] `pdm run run-local-pdm typecheck-all` passes.
- [ ] `pdm run run-local-pdm coverage-gate` remains >= 90%.
- [ ] `pdm run run-local-pdm validate-tasks` and `pdm run run-local-pdm validate-docs` pass.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
