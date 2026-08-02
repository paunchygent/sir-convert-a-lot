---
id: task-28-markdown-to-pdf-via-html-intermediary-pandoc-weasyprint
title: Markdown to PDF via HTML intermediary (Pandoc + WeasyPrint)
type: task
status: completed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-06-pandoc-weasyprint-document-converters-parity-md-pdf-docx-txt.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - md
  - html
  - pdf
  - pandoc
  - weasyprint
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the critical local pipeline `md -> html -> pdf` as a first-class Sir Convert-a-Lot route,
using an HTML intermediary by default for layout control.

## PR Scope

- Implement Markdown → standalone HTML rendering (Pandoc-driven) with deterministic title handling.
- Implement HTML → PDF conversion by delegating to the canonical HTML+CSS→PDF converter.
- CLI support for:
  - `convert-a-lot convert <md> --to pdf --output-dir <dir>`
  - optional `--css <path>` injection into the PDF rendering step,
  - optional debug flag to keep intermediate HTML artefacts.
- Dependency governance:
  - add/validate Python dependencies (Pandoc wrapper),
  - detect missing Pandoc binary and fail with deterministic error codes.
- Tests:
  - smoke fixture `md -> pdf` produces non-empty PDF,
  - deterministic manifest emission for a directory batch.

## Implementation Notes

- Build on shared primitives:
  - route selection from Task 31,
  - HTML→PDF from Task 32.
- Intermediate HTML policy:
  - default: delete intermediate HTML after successful PDF generation,
  - debug: keep intermediate HTML under a deterministic subfolder in `--output-dir`.
- CSS policy:
  - `--css` affects the PDF rendering stage; Markdown→HTML stage must remain deterministic
    regardless of CSS presence.

## Deliverables

- [x] Local `md -> html -> pdf` pipeline implementation under `scripts/sir_convert_a_lot/`.
- [x] CLI route wiring and flags documented in `docs/converters/sir_convert_a_lot.md`.
- [x] Fixtures + tests for success and missing dependency conditions.

## Acceptance Criteria

- [x] `convert-a-lot convert <md> --to pdf` produces a non-empty PDF via HTML intermediary.
- [x] Intermediate HTML handling is deterministic (kept/removed based on flag).
- [x] Missing Pandoc binary is detected and mapped to a deterministic error code.
- [x] Manifest entries are deterministic and stable for batch conversions.

## Validation Evidence

- Local quality gates:
  - 2026-02-18:
    - `pdm run run-local-pdm format-all` (pass)
    - `pdm run run-local-pdm lint-fix` (pass)
    - `pdm run run-local-pdm typecheck-all` (pass)
    - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -q` (pass)
    - `pdm run run-local-pdm validate-tasks` (pass)
    - `pdm run run-local-pdm validate-docs` (pass)
    - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
