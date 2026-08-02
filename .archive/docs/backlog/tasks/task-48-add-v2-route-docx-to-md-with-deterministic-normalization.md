---
id: task-48-add-v2-route-docx-to-md-with-deterministic-normalization
title: Add v2 route docx to md with deterministic normalization
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - markdown
  - route
  - docx
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement `docx -> md` as a first-class v2 route with deterministic normalization and predictable errors.

## PR Scope

- Extend v2 source format and route validators for DOCX input.
- Implement converter execution path for DOCX to Markdown.
- Apply normalization profile and warnings semantics consistently.
- Add route docs and examples for API + CLI use.

## Deliverables

- [x] `docx -> md` v2 route implemented end-to-end.
- [x] Deterministic normalization + metadata output for DOCX conversions.
- [x] Contract tests and fixture-based regression coverage.

## Acceptance Criteria

- [x] DOCX input can be submitted via v2 and returns Markdown artifact/result deterministically.
- [x] Invalid or corrupt DOCX inputs produce deterministic validation/input errors.
- [x] Route is documented in v2 converter contract and CLI usage docs.

## Execution Plan (Slice 48A, 2026-02-28)

1. Route contract expansion (no executor behavior yet):
   - add `docx` to `SourceFormatV2`,
   - add `docx -> md` to allowed v2 routes,
   - extend upload format inference to accept `.docx`,
   - extend v2 HTTP client content-type inference for `.docx`.
1. Dedicated converter module (SRP and file-size safety):
   - add `pandoc_docx_to_markdown.py` wrapper with deterministic error mapping:
     - `pandoc_not_installed` -> retryable/503 lane,
     - `docx_to_markdown_failed` -> non-retryable conversion failure lane.
1. Executor integration:
   - add `docx -> md` execution branch in v2 executor,
   - run strict markdown normalization (`none|standard|strict` via existing normalizer),
   - emit deterministic `pipeline_used` (`docx_to_md_v2`).
1. Validation semantics:
   - reject unreadable/corrupt DOCX with deterministic `422` input error (`docx_unreadable`),
   - keep md-output upload guards (`resources`, `reference_docx`) unchanged and covered.
1. CLI and route diagnostics:
   - add `docx -> md` to CLI v2 route registry and dry-run output,
   - remove pdf-only wording where `--to md` is now multi-source (`pdf` + `docx`).
1. Docs synchronization:
   - update v2 converter API route matrix and request examples,
   - update CLI converter docs to include `docx -> md` examples.
1. Tests and gates:
   - add/extend tests for model validation, route create behavior, executor branch, CLI routes, and
     contract lifecycle,
   - run full quality/docs gates before terminalization.

## Risk Controls

- File-size guard:
  - `v2_conversion_executor.py` is already above the 500 LoC soft limit; keep new conversion
    subprocess logic in a dedicated module and avoid large branch inflation.
- Determinism guard:
  - re-use existing markdown normalization utilities; do not create ad hoc markdown cleanup paths.
- Contract drift guard:
  - update API + CLI docs in the same slice as code/tests to avoid mismatch.

## Test Matrix (Minimum)

- Domain/model:
  - `tests/sir_convert_a_lot/test_specs_v2.py` (`docx -> md` route allowed, invalid combos rejected).
- HTTP create/result/artifact:
  - `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`
  - `tests/sir_convert_a_lot/test_api_contract_v2_docx_to_md.py` (docx->md lifecycle lane).
- Executor:
  - `tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py`,
  - `tests/sir_convert_a_lot/test_v2_conversion_executor_docx_to_md.py`.
- CLI:
  - `tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py`
  - `tests/sir_convert_a_lot/test_cli_v2_routes.py`.

## Validation Commands

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_specs_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_api_contract_v2_docx_to_md.py tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py tests/sir_convert_a_lot/test_v2_conversion_executor_docx_to_md.py tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py tests/sir_convert_a_lot/test_cli_v2_routes.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
