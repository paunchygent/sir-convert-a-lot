---
id: task-32-html-css-to-pdf-route-weasyprint-with-deterministic-manifest
title: HTML+CSS to PDF route (WeasyPrint) with deterministic manifest
type: task
status: completed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-09-template-driven-html-conversions-handout-builder-parity.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - html
  - pdf
  - weasyprint
  - css
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the critical local pipeline `html + css -> pdf` through the canonical CLI surface,
producing deterministic output files and deterministic manifest entries.

## PR Scope

- Add a local HTML-to-PDF converter implementation backed by WeasyPrint.
- CLI support for:
  - `convert-a-lot convert <html> --to pdf --output-dir <dir>`
  - optional `--css <path>` (explicit CSS injection) and base-url/asset resolution.
- Output policy:
  - deterministic output filename mapping (based on source name + target extension),
  - deterministic manifest emission (ordering and fields).
- Dependency governance:
  - add required Python deps,
  - document and (where applicable) install required OS packages in the Docker lane,
  - deterministic error code when WeasyPrint deps are missing.
- Tests:
  - minimal fixture HTML + CSS converted to non-empty PDF,
  - negative test path(s) for missing dependencies (deterministic error code).

## Implementation Notes

- Expected touchpoints:
  - New converter module under `scripts/sir_convert_a_lot/infrastructure/` (or equivalent).
  - CLI wiring through the route registry (`docs/backlog/tasks/task-31-cli-route-registry-for-local-and-hybrid-conversions.md`).
- Asset resolution:
  - Use an HTML base URL that preserves relative paths for images/fonts when converting from files.
  - CSS file paths should be resolved deterministically (absolute resolution at runtime is OK;
    emitted output filenames must remain stable).
- Determinism definition for this task:
  - deterministic output file paths and manifest entries,
  - PDF binary may include metadata that is not bit-for-bit stable; do not gate on identical bytes.

## Deliverables

- [x] WeasyPrint-backed converter module under `scripts/sir_convert_a_lot/`.
- [x] CLI flags and route wiring for `html + css -> pdf`.
- [x] Minimal fixtures + smoke tests for HTML/CSS rendering.
- [x] Docs updated with usage examples and dependency requirements.

## Acceptance Criteria

- [x] Converting a representative HTML + CSS fixture produces a non-empty PDF.
- [x] Output file naming and manifest entries are deterministic across runs.
- [x] Missing dependency conditions surface a deterministic error code and actionable message.
- [x] Tests and docs-as-code gates pass.

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
