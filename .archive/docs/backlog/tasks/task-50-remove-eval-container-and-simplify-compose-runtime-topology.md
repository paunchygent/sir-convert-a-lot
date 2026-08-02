---
id: task-50-remove-eval-container-and-simplify-compose-runtime-topology
title: Remove eval container and simplify compose runtime topology
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - runtime
  - docker
  - cleanup
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove eval-lane container complexity and keep one canonical runtime topology for production-oriented conversion workflows.

## PR Scope

- Remove eval container service definitions and associated profile paths.
- Remove eval app entrypoint/surfaces when no longer needed.
- Update runbooks and operational scripts for single-runtime assumptions.
- Keep readiness/liveness and GPU governance checks intact.

## Deliverables

- [x] Compose/runtime definitions simplified to one canonical conversion service topology.
- [x] Eval entrypoint codepaths removed or archived outside active runtime surface.
- [x] Operational docs and scripts updated.

## Acceptance Criteria

- [x] `docker compose config` exposes only one canonical conversion runtime service.
- [x] Eval runtime entrypoint and compose overlays are removed from active runtime surfaces.
- [x] Existing smoke checks pass against the single-runtime topology.
- [x] No active runbook/docs path requires eval container usage for normal operations.

## Sequencing and Dependencies

1. This is `T11` in Epic 05 and executes after `T10` (Task 52) by sprint-order policy.
1. Task 50 must complete before Task 51 (`T12`) so stale references can be purged against final
   runtime truth.
1. Task 12 benchmark dependency must be resolved during this slice by migrating benchmark/devops
   probes to v2 single-runtime behavior only (no eval-lane fallback).

## Execution Plan (Slice 50A, 2026-02-28)

1. Freeze runtime-cutover decision and dependency handling.
   - Rewrite Task 12 planning language to v2 single-runtime only to remove hidden eval coupling.
1. Remove eval runtime overlays from container topology.
   - Edit `compose.yaml` to remove `sir_convert_a_lot_eval`, eval port/env wiring, and eval volume.
   - Edit `Dockerfile` to remove eval-only exposure/comments.
   - Edit `pyproject.toml` to remove `serve:sir-convert-a-lot-eval`.
1. Remove eval app/readiness runtime branches.
   - Remove `scripts/sir_convert_a_lot/service_eval.py`.
   - Update `scripts/sir_convert_a_lot/interfaces/http_app_state.py` to remove eval-root helpers.
   - Update `scripts/sir_convert_a_lot/interfaces/http_routes_health.py` to remove prod/eval
     collision/readiness branches while preserving fail-closed revision/profile checks.
1. Update operational verification scripts to single-runtime + v2 contract.
   - Simplify `scripts/devops/verify-hemma-gpu-runtime.sh`:
     - remove eval listener/container assumptions,
     - migrate conversion probe from `/v1/convert/jobs*` to v2 lifecycle endpoints.
1. Rewrite runtime topology regression tests.
   - Update `tests/sir_convert_a_lot/test_compose_contract.py` for single-service invariants.
   - Update `tests/sir_convert_a_lot/test_service_import_side_effects.py` to remove
     `service_eval` import assertions.
   - Adjust any benchmark/devops tests that still assert eval topology.
1. Sync runbook/docs to single-runtime topology.
   - Update `docs/runbooks/runbook-hemma-devops-and-gpu.md` to remove `8086` and prod/eval overlay
     assumptions.
1. Run quality/docs gates and capture evidence in task + current-log.

## Risk Controls

- Task 12 legacy-evidence coupling risk:
  - do not delete or invalidate benchmark evidence; explicitly reframe historical artifacts if
    runtime coupling is removed.
- GPU governance regression risk:
  - keep fail-closed readiness/runtime checks and validate with Hemma verification script updates.
- Contract drift risk:
  - runtime, tests, and runbook changes must ship in the same slice.

## Test Matrix (Minimum)

- Compose/runtime contracts:
  - `tests/sir_convert_a_lot/test_compose_contract.py`
  - `tests/sir_convert_a_lot/test_dev_compose_wrapper.py`
- Entrypoint side effects:
  - `tests/sir_convert_a_lot/test_service_import_side_effects.py`
- API surface sanity after cutover:
  - `tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py`
- Benchmark/devops impacted lanes (if touched):
  - `tests/sir_convert_a_lot/test_benchmark_scientific_corpus.py`

## Validation Commands

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_service_import_side_effects.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Execution Outcome (Slice 50A, 2026-02-28)

- Removed eval runtime topology from active container/runtime surfaces:
  - `compose.yaml`: removed `sir_convert_a_lot_eval`, eval env wiring, and eval volume.
  - `Dockerfile`: removed eval root creation and `EXPOSE 8086`.
  - `pyproject.toml`: removed `serve:sir-convert-a-lot-eval`.
  - deleted `scripts/sir_convert_a_lot/service_eval.py`.
- Removed eval-branch readiness/runtime helpers:
  - `scripts/sir_convert_a_lot/interfaces/http_app_state.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_health.py`
- Reworked ops verification to single-runtime + v2 job lifecycle:
  - `scripts/devops/verify-hemma-gpu-runtime.sh`
- Reworked runtime topology regression tests for single runtime:
  - `tests/sir_convert_a_lot/test_compose_contract.py`
  - `tests/sir_convert_a_lot/test_service_import_side_effects.py`
- Updated runbook to single-runtime operational truth:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`

### Validation Evidence

- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_service_import_side_effects.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py` (pass: `17 passed`)
- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 142 source files`)
- `pdm run run-local-pdm coverage-gate` (pass: `347 passed, 5 skipped`; `Total coverage: 94.94%`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=104 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
