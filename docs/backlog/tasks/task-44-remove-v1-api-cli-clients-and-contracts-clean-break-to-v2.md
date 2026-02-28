---
id: task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2
title: Remove v1 API CLI clients and contracts clean break to v2
type: task
status: completed
priority: critical
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - v2
  - clean-break
  - api
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove v1 conversion surfaces and re-home required behavior in v2 so the platform has one API version only.

## PR Scope

- Remove v1 job routes and v1 client adapter usage from canonical paths.
- Add/lock `pdf -> md` under v2 route contract.
- Remove v1-specific compatibility logic from CLI routing.
- Remove v1 contract references from active converter docs where superseded.
- Preserve deterministic error envelope/idempotency behavior under v2.

## Deliverables

- [x] v1 runtime routes and CLI branch logic removed.
- [x] v2 `pdf -> md` route implemented and documented.
- [x] Tests migrated from v1-path assumptions to v2-path assumptions.
- [x] Docs updated for v2-only API usage.

## Acceptance Criteria

- [x] Requests to previous v1 conversion routes are no longer part of supported API surface.
- [x] CLI executes `pdf -> md` through v2 only.
- [x] Contract tests pass for v2 `pdf -> md` lifecycle and result retrieval.
- [x] No active docs recommend using v1 conversion endpoints.

## Execution Plan (Slice 44A, 2026-02-28)

1. Remove v1 conversion route registration from service wiring and runtime request surfaces.
1. Re-home `pdf -> md` route behavior under v2 route selection and v2 job-spec validation paths.
1. Remove CLI branch points that still resolve to v1 conversion endpoints.
1. Migrate/add contract tests that assert:
   - v1 conversion endpoints are absent/unsupported,
   - v2 `pdf -> md` submit/status/result/artifact flow is canonical.
1. Update converter docs to remove active v1 usage guidance and point to v2-only route semantics.
1. Run full quality/docs gates before closing this task:
   - `pdm run run-local-pdm format-all`
   - `pdm run run-local-pdm lint-fix`
   - `pdm run run-local-pdm typecheck-all`
   - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
   - `pdm run run-local-pdm coverage-gate`
   - `pdm run run-local-pdm validate-tasks`
   - `pdm run run-local-pdm validate-docs`
   - `pdm run run-local-pdm index-tasks --root \"$(pwd)/docs/backlog\" --out \"/tmp/sir_tasks_index.md\" --fail-on-missing`

## Next Executable Slice (44B, first real implementation slice)

1. Service route cutover
   - Remove v1 conversion route registration from service startup wiring.
   - Keep non-conversion v1 surfaces untouched unless explicitly linked to conversion pathing.
1. Runtime contract cutover
   - Remove runtime entry points that accept v1 conversion specs for active conversion flow.
   - Ensure v2 route registry explicitly includes `pdf -> md` and no v1 fallback.
1. CLI contract cutover
   - Remove CLI branch logic that submits conversion jobs to v1 endpoints.
   - Lock CLI route resolution so `pdf -> md` always resolves to v2.
1. Tests (must ship in same slice)
   - Add/update contract tests proving v1 conversion endpoints are no longer supported.
   - Add/update CLI tests proving `pdf -> md` uses v2 submit/status/result/artifact flow only.
1. Docs and contract sync (same PR)
   - Remove active v1 conversion usage from converter API docs and CLI docs.
   - Keep migration language explicit: clean break, no deprecation bridge.
1. Exit gates for Slice 44B
   - `pdm run run-local-pdm format-all`
   - `pdm run run-local-pdm lint-fix`
   - `pdm run run-local-pdm typecheck-all`
   - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_cli_v2_routes.py`
   - `pdm run run-local-pdm coverage-gate`
   - `pdm run run-local-pdm validate-tasks`
   - `pdm run run-local-pdm validate-docs`
   - `pdm run run-local-pdm index-tasks --root \"$(pwd)/docs/backlog\" --out \"/tmp/sir_tasks_index.md\" --fail-on-missing`

## Execution Outcome (Slice 44B, 2026-02-28)

- Removed v1 conversion route registration from HTTP service wiring.
- Removed CLI v1 conversion branching; all conversion submissions route through v2 client.
- Added/locked v2 `pdf -> md` route support in contracts/runtime/artifact metadata.
- Migrated contract coverage:
  - v2 lifecycle coverage for `pdf -> md`,
  - explicit assertions that v1 conversion routes are absent.
- Updated converter docs to v2-only active usage and downgraded legacy v1 guidance.
- Enforced strict LoC compliance for touched modules (`<500`), including `job_store_v2_core.py`.

### Validation Evidence

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass; `Success: no issues found in 127 source files`)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot` (pass; `298 passed, 5 skipped`)
- `pdm run run-local-pdm coverage-gate` (pass; `Total coverage: 96.10%`)
- `pdm run run-local-pdm validate-tasks` (pass; `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass; `Validated docs=102 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
