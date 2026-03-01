---
id: 'task-66-add-v2-route-docx-to-pdf-via-pandoc-html-and-weasyprint'
title: 'Add v2 route DOCX to PDF via Pandoc HTML and WeasyPrint'
type: 'task'
status: 'proposed'
priority: 'high'
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

- [ ] `docx -> pdf` is an allowed v2 route (`JobSpecV2` validation).
- [ ] Executor supports `docx -> pdf` with `pipeline_used == "docx_to_pdf_v2"`.
- [ ] New Pandoc wrapper exists for `docx -> html` and includes `--sandbox`.
- [ ] CLI route registry includes `docx -> pdf`.
- [ ] `docs/converters/multi_format_conversion_service_api_v2.md` updated with route + example spec.
- [ ] `docs/converters/downstream_integration_contract_v2.md` updated with route + example spec.
- [ ] Tests cover spec validation, executor behavior, wrapper command construction, and API artifact contract.

## Acceptance Criteria

- [ ] API v2 accepts `docx -> pdf` jobs and produces `application/pdf` artifacts.
- [ ] All Pandoc invocations in this new route include `--sandbox`.
- [ ] WeasyPrint runs with restricted resource fetching rooted in the job workdir.
- [ ] `pdm run run-local-pdm typecheck-all` passes.
- [ ] `pdm run run-local-pdm coverage-gate` remains >= 90%.
- [ ] `pdm run run-local-pdm validate-tasks` and `pdm run run-local-pdm validate-docs` pass.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
