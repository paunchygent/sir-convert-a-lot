---
id: task-47-implement-docx-template-endpoints-validation-and-fixture-templates
title: Implement docx template endpoints validation and fixture templates
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
labels:
  - template
  - api
  - validation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement API-ready template catalog behavior with real reference templates and robust validation.

## PR Scope

- Add template catalog endpoints (list/get and selection-ready payloads).
- Add template ingestion/validation flow as allowed by contract.
- Add initial practical template fixtures for real production use.
- Integrate template selection into DOCX-producing conversion routes.

## Deliverables

- [x] Working template catalog API surface.
- [x] Validation logic + deterministic error mapping.
- [x] Minimum three practical fixture templates available.
- [x] Converter docs updated with template usage examples.

## Acceptance Criteria

- [x] Template list/get routes are stable and typed.
- [x] Template-selected conversions produce non-empty DOCX artifacts.
- [x] Unknown template IDs return deterministic validation errors.

## Execution Plan (Slice 47A, 2026-02-28)

1. Add a typed template catalog subsystem:
   - metadata models + loader + sha256/size verification.
1. Add template catalog read endpoints:
   - `GET /v2/templates/docx`
   - `GET /v2/templates/docx/{template_id}`
   - `GET /v2/templates/docx/{template_id}/versions/{version}`
1. Add typed selector semantics to v2 job spec (`conversion.template`) with deterministic validation.
1. Integrate selector resolution into DOCX-producing routes and conversion execution.
1. Add at least three curated fixture templates with metadata.
1. Add/expand tests for:
   - template catalog list/get routes,
   - unknown template id/version deterministic errors,
   - template-selected DOCX conversion success path.
1. Run quality and docs gates before terminalization.

## Execution Outcome (Slice 47A, 2026-02-28)

- Implemented typed template catalog subsystem:
  - `scripts/sir_convert_a_lot/infrastructure/docx_template_catalog_v2.py`
  - deterministic metadata parsing, integrity checks, and selector resolution.
- Added read-only v2 template discovery routes:
  - `GET /v2/templates/docx`
  - `GET /v2/templates/docx/{template_id}`
  - `GET /v2/templates/docx/{template_id}/versions/{version}`
  - implementation: `scripts/sir_convert_a_lot/interfaces/http_routes_templates_v2.py`
- Integrated typed template selector semantics into v2 job spec:
  - `conversion.template` with deterministic validation
  - disallowed mixed `template` + `reference_docx_filename`
  - implementation: `scripts/sir_convert_a_lot/domain/specs_v2.py`
- Added deterministic create-job validation mappings for unknown template ids/versions and
  unavailable templates:
  - `scripts/sir_convert_a_lot/interfaces/http_jobs_v2_request_validation.py`
  - integrated in `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
- Added curated fixture templates (three practical references):
  - `scripts/sir_convert_a_lot/templates/docx/academic-report/1.0.0/template.docx`
  - `scripts/sir_convert_a_lot/templates/docx/classroom-handout/1.0.0/template.docx`
  - `scripts/sir_convert_a_lot/templates/docx/project-week-summary/1.0.0/template.docx`
  - each with checked `metadata.json`.
- Added template audit metadata to successful DOCX result metadata:
  - `template_id`, `template_version`, `template_artifact_sha256`
  - propagated through executor/runtime/store/contracts.
- Added/updated tests for template store, endpoints, create-job validation, v2 spec validation, and
  template-selected DOCX contract behavior.
- Updated converter contract docs with active template endpoint and selector semantics:
  - `docs/converters/multi_format_conversion_service_api_v2.md`

### Validation Evidence

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass; `Success: no issues found in 134 source files`)
- `pdm run run-local-pdm coverage-gate` (pass; `Total coverage: 95.41%`)
- `pdm run run-local-pdm validate-tasks` (pass; `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass; `Validated docs=103 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
