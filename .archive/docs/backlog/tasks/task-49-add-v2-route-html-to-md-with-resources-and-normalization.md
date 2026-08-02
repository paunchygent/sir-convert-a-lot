---
id: task-49-add-v2-route-html-to-md-with-resources-and-normalization
title: Add v2 route html to md with resources and normalization
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
  - html
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement `html -> md` as a first-class v2 route with deterministic handling of resources and normalization.

## PR Scope

- Extend v2 route validator and executor for HTML to Markdown conversion.
- Reuse resources bundle extraction and enforce clear resource-resolution semantics.
- Apply deterministic Markdown normalization and warning behavior.
- Add contract + usage docs for HTML markdown-ingress workflows.

## Deliverables

- [x] `html -> md` v2 route implemented.
- [x] Resource-resolution behavior documented and tested.
- [x] Deterministic normalization and error mapping for missing/invalid resources.

## Acceptance Criteria

- [x] HTML input converts to Markdown under v2 lifecycle semantics.
- [x] Missing required resources produce deterministic, actionable errors.
- [x] Route appears in CLI route diagnostics and API docs.

## Execution Plan (Slice 49A, 2026-02-28)

1. Route contract expansion and guard policy alignment:
   - add `html -> md` to v2 allowed routes in `specs_v2`,
   - update route-option guard logic to allow `resources` only for `html -> md`,
   - keep `resources` rejected for `pdf -> md` and `docx -> md`,
   - keep `reference_docx` rejected for all Markdown-target routes.
1. Dedicated converter module for SRP + deterministic failures:
   - add `pandoc_html_to_markdown.py` wrapper (typed error model, deterministic codes),
   - use Pandoc HTML reader + GFM writer with explicit resource search-path configuration.
1. Resource resolution and missing-resource determinism:
   - validate local HTML resource references before conversion against extracted workdir,
   - return deterministic `422` input errors for missing required local resources,
   - ensure remote URLs are not treated as local-missing-resource failures.
1. Executor integration and normalization:
   - add `html -> md` execution branch in v2 executor with pipeline key `html_to_md_v2`,
   - run `normalize_markdown_for_v2_md_output(..., mode=strict)` and persist warnings,
   - map converter/runtime failures to deterministic retryable/non-retryable service errors.
1. CLI route + payload behavior:
   - add `html -> md` route to CLI registry and dry-run route diagnostics,
   - permit `--resources` for `html -> md` while keeping `--css` and `--reference-docx`
     disallowed for Markdown targets.
1. Docs synchronization:
   - update v2 API contract route matrix and request semantics for `html -> md`,
   - publish deterministic route-specific error semantics for `html -> md`,
   - update CLI usage docs and route-disambiguation language (`--to md` now includes html).
1. Validation and closeout:
   - run quality/docs gates,
   - keep story/epic check ordering strict (`T09` unchecked until Task 49 is terminal).

## Risk Controls

- File-size/SRP guard:
  - `v2_conversion_executor.py` is already above 500 LoC; keep new Pandoc/resource-validation logic
    outside the executor module and only add narrow branch wiring.
- Contract drift guard:
  - update Task 49 + converter docs + CLI usage docs in the same slice to avoid temporary route
    mismatch.
- Resource-policy drift guard:
  - enforce one explicit policy in code + docs:
    - `resources` allowed only for `html -> md`,
    - `resources` rejected for other Markdown-target routes.
- Determinism guard:
  - use stable route error codes/details for missing local resources and converter failures.

## Test Matrix (Minimum)

- Domain/model:
  - `tests/sir_convert_a_lot/test_specs_v2.py` (`html -> md` route acceptance and unsupported-route rejection).
- HTTP create-route constraints:
  - `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`
    (allow resources for `html -> md`; reject resources for `pdf/docx -> md`).
- API contract lifecycle:
  - `tests/sir_convert_a_lot/test_api_contract_v2_html_to_md.py` (new).
- Converter + executor:
  - `tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py` (new),
  - `tests/sir_convert_a_lot/test_v2_conversion_executor_html_to_md.py` (new).
- CLI route diagnostics + execution:
  - `tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py`,
  - `tests/sir_convert_a_lot/test_cli_v2_routes.py`.

## Validation Commands

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_specs_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_api_contract_v2_html_to_md.py tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py tests/sir_convert_a_lot/test_v2_conversion_executor_html_to_md.py tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py tests/sir_convert_a_lot/test_cli_v2_routes.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
