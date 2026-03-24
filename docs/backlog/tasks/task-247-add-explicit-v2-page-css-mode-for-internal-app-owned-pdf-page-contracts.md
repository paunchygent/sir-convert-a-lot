---
id: task-247-add-explicit-v2-page-css-mode-for-internal-app-owned-pdf-page-contracts
title: Add explicit v2 page CSS mode for internal-app-owned PDF page contracts
type: task
status: completed
priority: high
created: '2026-03-24'
last_updated: '2026-03-24'
related:
  - docs/backlog/stories/story-16-v2-pdf-layout-presets-docx-to-pdf-route.md
  - docs/backlog/tasks/task-65-add-v2-pdf-layout-presets-paper-orientation-for-pdf-outputs.md
  - docs/decisions/0004-v2-pdf-layout-presets-preview-docx-to-pdf.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - scripts/sir_convert_a_lot/domain/specs_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py
  - scripts/sir_convert_a_lot/infrastructure/v2_non_pdf_helpers.py
  - tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py
labels:
  - v2
  - pdf
  - contract
  - downstream
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add an explicit v2 contract switch so internal application callers can choose a
fully author-owned PDF page-CSS path without overloading the existing
`conversion.pdf_layout` preset lane.

## PR Scope

Extend the v2 PDF contract with one explicit mode field:

- `conversion.page_css_mode = "preset_append" | "author_owned"`

Semantics to lock in this task:

- `preset_append`
  - preserves current behavior;
  - is intended for quick one-off callers that want typed
    paper/orientation/margin presets through `conversion.pdf_layout`;
  - continues to append the generated preset stylesheet after caller CSS.
- `author_owned`
  - is the canonical path for full downstream applications that provide their
    own page contract in author CSS;
  - forbids `conversion.pdf_layout`;
  - must not append any service-owned preset page stylesheet.

Implementation must:

- update the normative API and downstream integration docs;
- update the v2 spec validation rules and examples;
- make stylesheet resolution deterministic and mode-aware for all PDF-output
  routes;
- preserve current default behavior for existing preset-based callers.

Out of scope:

- redesigning non-PDF routes;
- removing `conversion.pdf_layout`;
- changing artifact lifecycle, webhook, or retention behavior.

## Deliverables

- [x] `conversion.page_css_mode` added to the v2 contract with explicit schema,
  defaults, and route constraints.
- [x] `docs/converters/multi_format_conversion_service_api_v2.md` updated with
  normative semantics and examples for both modes.
- [x] `docs/converters/downstream_integration_contract_v2.md` updated to define:
  - quick preset callers use `preset_append`;
  - internal/full-application callers use `author_owned`.
- [x] Spec validation tests cover:
  - default mode behavior,
  - `author_owned` forbidding `pdf_layout`,
  - non-PDF route constraints.
- [x] Executor tests cover stylesheet resolution behavior for both modes.

## Acceptance Criteria

- [x] A v2 PDF job that omits `page_css_mode` behaves exactly like today and
  preserves preset-append behavior.
- [x] A v2 PDF job with `page_css_mode = "author_owned"` and author `@page` CSS
  is accepted without any appended preset page stylesheet.
- [x] A v2 PDF job with `page_css_mode = "author_owned"` and
  `conversion.pdf_layout` is rejected with a deterministic validation error.
- [x] The downstream integration contract clearly distinguishes quick one-offs
  from full application callers so products do not reverse-engineer page-CSS
  precedence from implementation details.
- [x] Docs and tests together make the page-CSS precedence model explicit enough
  that WeasyPrint-backed callers can rely on it intentionally, not accidentally.

## Validation Commands

- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_specs_v2.py tests/sir_convert_a_lot/test_v2_conversion_executor_pdf_layout.py tests/sir_convert_a_lot/test_api_contract_v2_docx_to_pdf.py`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
