---
id: task-30-markdown-to-docx-via-html-intermediary-pandoc
title: Markdown to DOCX via HTML intermediary (Pandoc)
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
  - docx
  - pandoc
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the critical local pipeline `md -> html -> docx` as the default DOCX export route,
to enable tighter layout control than direct `md -> docx`.

## PR Scope

- Implement Markdown → HTML rendering with a documented template strategy (minimum: one default).
- Implement HTML → DOCX conversion via Pandoc, with optional `--reference-docx` support.
- CLI support for:
  - `convert-a-lot convert <md> --to docx --output-dir <dir>`
  - optional HTML template selection / options where needed for layout control,
  - optional debug flag to keep intermediate HTML artefacts.
- Dependency governance:
  - detect missing Pandoc binary and fail with deterministic error codes.
- Tests:
  - smoke fixture `md -> docx` produces a non-empty DOCX,
  - manifest emission for directory batches.

## Implementation Notes

- HTML intermediary is the default:
  - do not implement direct `md -> docx` as the primary path; keep it as an internal option only
    if needed for parity/debugging.
- Reference styling:
  - `--reference-docx` should be optional and should not be required for basic conversions.
- Intermediate HTML policy mirrors Task 28 (`--keep-html` behavior and deterministic folder layout).

## Deliverables

- [x] Local `md -> html -> docx` pipeline implementation under `scripts/sir_convert_a_lot/`.
- [x] CLI route wiring + flags documented in `docs/converters/sir_convert_a_lot.md`.
- [x] Fixtures + tests for conversion success and missing dependency conditions.

## Acceptance Criteria

- [x] `convert-a-lot convert <md> --to docx` produces a non-empty DOCX via HTML intermediary.
- [x] Optional `--reference-docx` is supported and documented.
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
