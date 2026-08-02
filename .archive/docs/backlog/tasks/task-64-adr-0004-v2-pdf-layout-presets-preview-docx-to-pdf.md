---
id: task-64-adr-0004-v2-pdf-layout-presets-preview-docx-to-pdf
title: 'ADR-0004: v2 PDF layout presets + preview + DOCX to PDF'
type: task
status: completed
priority: high
created: '2026-03-01'
last_updated: '2026-03-01'
related:
  - docs/decisions/0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md
  - docs/backlog/stories/story-16-v2-pdf-layout-presets-docx-to-pdf-route.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
labels:
  - adr
  - v2
  - pdf
  - docx
  - contract
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Create and land ADR-0004 as the decision anchor for:

- first-class v2 PDF layout presets,
- `docx -> pdf` as a supported v2 route,
- “preview” semantics as a normal v2 job producing a normal PDF artifact.

This task exists to make Tasks 65 and 66 mechanically executable without later contract drift.

## PR Scope

Docs-only slice:

- finalize ADR-0004 content and links,
- ensure converter docs and downstream integration contract reference the ADR and state the intended
  contract surface.

## Deliverables

- [x] ADR-0004 complete and consistent:
  [0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/decisions/0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md)
- [x] `docs/converters/multi_format_conversion_service_api_v2.md` updated to reference ADR-0004 and reserve the
  contract surface.
- [x] `docs/converters/downstream_integration_contract_v2.md` updated to reference ADR-0004 and reserve the
  contract surface.

## Acceptance Criteria

- [x] ADR-0004 defines `conversion.pdf_layout` schema intent and validation rules at a level sufficient to
  implement.
- [x] ADR-0004 defines `docx -> pdf` pipeline choice and security invariants (Pandoc sandbox + WeasyPrint
  workdir-only).
- [x] ADR-0004 defines preview semantics (no separate engine/output format; normal v2 job + retention policy).
- [x] `pdm run run-local-pdm validate-docs` passes.
- [x] `pdm run run-local-pdm validate-tasks` passes.

## Validation Commands

- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm validate-tasks`

## Validation Evidence

- [x] Docs gates:
  - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=115 rules=9`, 2026-03-01).
  - `pdm run run-local-pdm validate-tasks` (pass: `Validated 92 backlog files`, 2026-03-01).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
