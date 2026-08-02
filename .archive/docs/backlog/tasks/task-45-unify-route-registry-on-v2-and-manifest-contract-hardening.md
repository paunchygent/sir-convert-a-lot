---
id: task-45-unify-route-registry-on-v2-and-manifest-contract-hardening
title: Unify route registry on v2 and manifest contract hardening
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - routing
  - manifest
  - contract
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Create one explicit route contract and manifest semantics that downstream GUI clients can reason about deterministically.

## PR Scope

- Refactor route registry to v2-only route taxonomy.
- Add explicit route metadata for CLI/API diagnostics (`source_format`, `target_format`, `pipeline_used`).
- Harden manifest schema so route/version semantics are explicit and stable.
- Tighten route-aware option validation to avoid implicit no-op flags.

## Deliverables

- [x] v2-only route registry with typed metadata.
- [x] Manifest schema extension and docs for deterministic GUI orchestration.
- [x] Validation errors that clearly state route-option incompatibilities.

## Acceptance Criteria

- [x] `convert-a-lot routes` and `--dry-run` show only v2 route graph.
- [x] Manifest fields are sufficient to correlate jobs to route contract and artifact behavior.
- [x] Route-option misuse produces deterministic, actionable errors.

## Execution Plan (Slice 45A, 2026-02-28)

1. Tighten v2 route-option validation parity:
   - reject `resources` and `reference_docx` for v2 `pdf -> md` requests in API create-job path.
1. Harden deterministic route metadata in CLI manifest:
   - include explicit `source_format`, `target_format`, and `pipeline_used` per entry.
1. Strengthen contract tests:
   - strict expected create/replay status behavior in no-op async test lanes,
   - route-table-level assertions that v1 conversion routes are absent,
   - explicit artifact `Content-Type` assertions for `pdf -> md`.
1. Strengthen CLI tests:
   - verify idempotency/correlation wiring is propagated,
   - verify manifest route metadata fields are present and deterministic.
1. Run validation gates for Slice 45A:
   - `pdm run run-local-pdm format-all`
   - `pdm run run-local-pdm lint-fix`
   - `pdm run run-local-pdm typecheck-all`
   - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py`
   - `pdm run run-local-pdm validate-tasks`
   - `pdm run run-local-pdm validate-docs`
   - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Execution Outcome (Slice 45A, 2026-02-28)

- Hardened API route-option validation parity:
  - v2 create-job now rejects `resources` and `reference_docx` uploads when `output_format="md"`.
- Hardened CLI manifest route metadata:
  - added deterministic per-entry fields: `source_format`, `target_format`, `pipeline_used`.
- Hardened contract tests:
  - strict status assertions for no-op async create/replay lanes,
  - route-table assertion that `/v1/convert/jobs*` routes are not registered,
  - artifact response `Content-Type` assertion for `pdf -> md`.
- Hardened CLI integration tests:
  - assert idempotency/correlation propagation to v2 client,
  - assert manifest route metadata fields for success/running entries.
- Hardened adapter conformance test lane:
  - added deterministic non-GPU E2E submit/poll/fetch + idempotent replay coverage.
- Updated converter docs:
  - v2 API contract now explicitly documents md-output route restrictions for uploads,
  - CLI converter doc now documents expanded deterministic manifest fields.

### Validation Evidence

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass; `Success: no issues found in 127 source files`)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py` (pass; `55 passed, 3 skipped`)
- `pdm run run-local-pdm coverage-gate` (pass; `Total coverage: 96.14%`)
- `pdm run run-local-pdm validate-tasks` (pass; `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass; `Validated docs=102 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
