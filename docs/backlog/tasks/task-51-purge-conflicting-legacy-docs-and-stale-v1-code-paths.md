---
id: task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths
title: Purge conflicting legacy docs and stale v1 code paths
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md
labels:
  - cleanup
  - docs
  - v1-removal
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove stale and conflicting docs/code references so the codebase narrative is consistent and easy to reason about.

## PR Scope

- Remove/replace stale references to v1 coexistence and local/hybrid converter behavior.
- Clean stale module docstrings that no longer match runtime behavior.
- Remove conflicting docs around capability matrix and route policy where outdated.
- Ensure converter/API docs describe only active architecture and routes.

## Deliverables

- [x] Converter, runbook, reference, and README docs aligned to active v2-only architecture.
- [x] Stale v1/local-hybrid code path references removed from active modules.
- [x] Deterministic v2-only hygiene checks added for active docs/code surfaces.
- [x] Validation gates and indexing pass after cleanup.

## Acceptance Criteria

- [x] Active docs and runtime modules expose one v2-only conversion narrative.
- [x] Grep-based hygiene checks pass with explicit active-surface scope and allowlist.
- [x] No active runtime code path depends on `/v1/convert/jobs*` or eval-service entrypoints.
- [x] Backlog current-context references are synchronized with Epic 05 sequencing and status policy.

## Sequencing and Dependencies

1. This is `T12` in Epic 05 and runs after Task 50 (`T11`) so cleanup targets finalized runtime.
1. Task 52 (`T10`) should be completed first so downstream contract links replace legacy adapter/v1
   references before cleanup removes conflicting docs.
1. This task removes conflicting references from all active docs/runtime paths; no fallback or
   coexistence language may remain in active guidance.

## Active Surface Definition (Hygiene Scope)

Use this scope for deterministic v2-only hygiene checks:

- `README.md`
- `scripts/sir_convert_a_lot/README.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/docx-template-catalog-contract-v2.md`
- `docs/converters/sir_convert_a_lot.md`
- `docs/converters/downstream_integration_contract_v2.md` (from Task 52)
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`
- `scripts/sir_convert_a_lot/interfaces/`
- `scripts/sir_convert_a_lot/integrations/`
- `scripts/devops/`

## Execution Plan (Slice 51A, 2026-02-28)

1. Establish v2-only hygiene baseline and allowlist policy.
   - Capture current grep baseline and define allowed legacy mentions
     (for example historical docs or explicit v1-absence tests).
1. Purge conflicting active docs guidance.
   - Remove v1/compatibility-local-hybrid guidance from active README/converter/runbook surfaces.
   - Ensure active docs link to v2-only conversion contract + downstream integration contract.
1. Remove stale runtime code paths and aliases.
   - Delete or retire unused v1 router/client surfaces in active modules.
   - Replace stale imports/aliases so active CLI/integration code paths are v2-only.
1. Update devops/benchmark helper surfaces that still hard-code v1 conversion routes in active flow.
1. Add deterministic hygiene checks (script or tests) for active surfaces and keep allowlist explicit.
1. Sync backlog current-log references and close with validation evidence.

## Risk Controls

- Over-cleanup risk:
  - do not rewrite historical decision records; preserve them as archival evidence and avoid breaking
    references by accident.
- Hidden v1-runtime dependency risk:
  - run targeted tests for CLI, adapters, and contract v1-absence assertions in the same slice.
- Docs/runtime divergence risk:
  - active docs updates must ship in the same PR as runtime cleanup.

## Test Matrix (Minimum)

- API/route absence and v2 contract:
  - `tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py`
  - `tests/sir_convert_a_lot/test_api_contract_v2.py`
- CLI and route diagnostics:
  - `tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py`
  - `tests/sir_convert_a_lot/test_cli_v2_routes.py`
  - `tests/sir_convert_a_lot/test_convert_a_lot_cli.py`
- Integration adapter conformance:
  - `tests/sir_convert_a_lot/test_integration_adapter_conformance.py`
- Runtime helpers impacted by v1 cleanup (if touched):
  - `tests/sir_convert_a_lot/test_v2_conversion_executor_docx_paths.py`
  - `tests/sir_convert_a_lot/test_runtime_conversion_quality_warnings.py`

## Validation Commands

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- `rg -n "/v1/convert/jobs|serve:sir-convert-a-lot-eval|sir_convert_a_lot_eval|service_eval" README.md scripts/sir_convert_a_lot/README.md docs/converters/multi_format_conversion_service_api_v2.md docs/converters/docx-template-catalog-contract-v2.md docs/converters/sir_convert_a_lot.md docs/converters/downstream_integration_contract_v2.md docs/runbooks/runbook-hemma-devops-and-gpu.md scripts/sir_convert_a_lot/interfaces scripts/sir_convert_a_lot/integrations scripts/devops`

## Execution Outcome (Slice 51A, 2026-02-28)

- Purged stale active-surface docs and route narratives to strict v2-only behavior:
  - `README.md`
  - `scripts/sir_convert_a_lot/README.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
- Removed stale interface/runtime code paths from active modules:
  - deleted `scripts/sir_convert_a_lot/interfaces/http_routes_jobs.py`
  - converted `scripts/sir_convert_a_lot/interfaces/http_client.py` to v2-only transport compatibility
  - simplified `scripts/sir_convert_a_lot/interfaces/cli_routes.py` to service-only route kind
  - removed path-based v1 error-envelope branch in `scripts/sir_convert_a_lot/interfaces/http_api.py`
- Updated active devops verification helper to strict v2 route set:
  - `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py`
- Verified active-surface hygiene baseline:
  - no active `LOCAL`/`HYBRID` pipeline enums,
  - no active `/v1/convert/jobs*` runtime-route dependencies in active docs/interfaces/devops surfaces.

### Validation Evidence

- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py` (pass: `37 passed, 3 skipped`)
- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 142 source files`)
- `pdm run run-local-pdm coverage-gate` (pass: `347 passed, 5 skipped`; `Total coverage: 94.94%`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=104 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
- Active-surface hygiene check (pass):
  - `rg -n "/v1/convert/jobs|serve:sir-convert-a-lot-eval|sir_convert_a_lot_eval|service_eval|LOCAL|HYBRID|local/hybrid|v1 conversion|v1 client" README.md scripts/sir_convert_a_lot/README.md docs/converters/multi_format_conversion_service_api_v2.md docs/converters/docx-template-catalog-contract-v2.md docs/converters/sir_convert_a_lot.md docs/converters/downstream_integration_contract_v2.md docs/runbooks/runbook-hemma-devops-and-gpu.md scripts/sir_convert_a_lot/interfaces scripts/sir_convert_a_lot/integrations scripts/devops`
  - only explicit v1-absence statements remain in converter docs.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
