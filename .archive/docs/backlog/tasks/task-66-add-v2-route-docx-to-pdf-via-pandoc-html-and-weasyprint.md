---
id: task-66-add-v2-route-docx-to-pdf-via-pandoc-html-and-weasyprint
title: Add v2 route DOCX to PDF via Pandoc HTML and WeasyPrint
type: task
status: completed
priority: high
created: '2026-03-01'
last_updated: '2026-03-01'
related:
  - docs/backlog/stories/story-16-v2-pdf-layout-presets-docx-to-pdf-route.md
  - docs/backlog/tasks/task-64-adr-0004-v2-pdf-layout-presets-preview-docx-to-pdf.md
  - docs/backlog/tasks/task-65-add-v2-pdf-layout-presets-paper-orientation-for-pdf-outputs.md
  - docs/decisions/0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md
  - scripts/sir_convert_a_lot/domain/specs_v2.py
  - scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py
  - scripts/sir_convert_a_lot/interfaces/cli_routes.py
labels:
  - v2
  - docx
  - pdf
  - route
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add `docx -> pdf` as a supported, sandboxed v2 route so downstream products can request PDF artifacts
from DOCX inputs without any ad hoc conversion tooling.

## PR Scope

Implementation requirements:

- Extend v2 route allowlist to include `docx -> pdf`.
- Implement pipeline as `docx -> html (pandoc, sandboxed, extract media) -> pdf (weasyprint, workdir-only)`.
- Add a dedicated Pandoc wrapper for `docx -> html` so the route is deterministic and separately testable.
- Wire the route in executor and CLI route registry.
- Ensure irrelevant uploads (example: reference docx) remain rejected deterministically for PDF outputs.

## Deliverables

- [x] `docx -> pdf` is an allowed v2 route (`JobSpecV2` validation).
- [x] Executor supports `docx -> pdf` with `pipeline_used == "docx_to_pdf_v2"`.
- [x] New Pandoc wrapper exists for `docx -> html` and includes `--sandbox`.
- [x] CLI route registry includes `docx -> pdf`.
- [x] `docs/converters/multi_format_conversion_service_api_v2.md` updated with route + example spec.
- [x] `docs/converters/downstream_integration_contract_v2.md` updated with route + example spec.
- [x] Tests cover spec validation, executor behavior, wrapper command construction, and API artifact contract.

## Acceptance Criteria

- [x] API v2 accepts `docx -> pdf` jobs and produces `application/pdf` artifacts.
- [x] All Pandoc invocations in this new route include `--sandbox`.
- [x] WeasyPrint runs with restricted resource fetching rooted in the job workdir.
- [x] `pdm run run-local-pdm typecheck-all` passes.
- [x] `pdm run run-local-pdm coverage-gate` remains >= 90%.
- [x] `pdm run run-local-pdm validate-tasks` and `pdm run run-local-pdm validate-docs` pass.

## Validation Commands

- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_pandoc_docx_to_html.py tests/sir_convert_a_lot/test_v2_conversion_executor_docx_to_pdf.py tests/sir_convert_a_lot/test_api_contract_v2_docx_to_pdf.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`

## Validation Evidence

- [x] Lint:
  - `pdm run run-local-pdm lint-fix` (pass: `All checks passed!`, 2026-03-01).
- [x] Type safety:
  - `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 167 source files`, 2026-03-01).
- [x] Full coverage gate:
  - `pdm run run-local-pdm coverage-gate` (pass: `416 passed, 5 skipped`; total coverage `95.29%`, 2026-03-01).
- [x] Docs gates:
  - `pdm run run-local-pdm validate-tasks` (pass: `Validated 92 backlog files`, 2026-03-01).
  - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=115 rules=9`, 2026-03-01).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
