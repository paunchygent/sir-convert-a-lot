---
id: task-19-fastapi-lifecycle-and-readiness-contract-replacing-script-band-aids
title: FastAPI lifecycle and readiness contract replacing script band-aids
type: task
status: completed
priority: critical
created: '2026-02-15'
last_updated: '2026-02-16'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-18-root-cause-fix-deterministic-service-execution-and-artifact-integrity.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - fastapi
  - lifecycle
  - readiness
  - architecture
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace script-heavy runtime correctness checks with a canonical FastAPI service
lifecycle/readiness contract aligned with HuleEdu service patterns, so deploy
correctness is guaranteed by app/supervisor semantics instead of ad hoc guards.

## PR Scope

Architecture scope:

- Define canonical app factory and lifespan bootstrap for prod/eval profiles.
- Move runtime ownership and startup invariants into app lifecycle (`app.state`).
- Add readiness endpoint semantics that enforce revision/profile/data-root invariants.
- Keep `/healthz` as liveness only; move deploy-correctness gates to `/readyz`.
- Keep wrapper scripts minimal transport/orchestration only.

Out of scope:

- changes to conversion quality heuristics,
- Task 12 scoring/ranking logic,
- replacing Hemma supervisor stack in this slice.

## Locked Decisions

1. No new brittle script-only band-aids.
1. Service correctness must be app-driven (FastAPI lifecycle + readiness contract).
1. Readiness must fail closed on revision/config/profile mismatch.
1. Prod/eval isolation is an app invariant, not an operator memory task.
1. Task 19 starts after Task 18 merge boundary is stable.

## Deliverables

- [x] `http_api` exposes canonical factory-only setup with deterministic lifespan hooks
- [x] `service.py` and `service_eval.py` are explicit profile entrypoints only
- [x] `/readyz` endpoint returns deterministic readiness verdict + reasons
- [x] `verify-hemma-gpu-runtime` consumes `/readyz` contract rather than bespoke checks
- [x] Tests cover readiness mismatch cases (revision/profile/data-root/isolation)
- [x] Runbook updated to the new canonical deploy-verification flow

## Acceptance Criteria

- [x] Service fails readiness when running stale revision after `git pull`
- [x] Service fails readiness when eval/prod data roots collide
- [x] Service fails readiness when profile does not match configured entrypoint
- [x] Startup/import side-effects are absent and regression tested
- [x] Existing API v1 behavior remains contract-compatible
- [x] Task 18 script complexity can be reduced without loss of safety guarantees

## Implementation Plan

1. Introduce typed service metadata model for runtime revision/profile/data-root/start time.
1. Centralize app bootstrapping in `create_app(..., profile=...)` with lifespan initialization.
1. Add `/readyz` and contract tests for pass/fail matrix.
1. Simplify `verify-hemma-gpu-runtime.sh` to trust service readiness contract.
1. Update runbook and active context docs with the canonical flow.

## Validation Plan

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence

- Refactor surfaces (HuleEdu-aligned app/route split):
  - `scripts/sir_convert_a_lot/interfaces/http_api.py`
  - `scripts/sir_convert_a_lot/interfaces/http_app_state.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_jobs.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_health.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_models.py`
  - `scripts/sir_convert_a_lot/service.py`
  - `scripts/sir_convert_a_lot/service_eval.py`
  - `scripts/devops/verify-hemma-gpu-runtime.sh`
- Readiness coverage added:
  - `tests/sir_convert_a_lot/test_api_contract_v1.py`
  - `tests/sir_convert_a_lot/test_service_import_side_effects.py`
- Local quality/docs gates:
  - `pdm run format-all` (pass)
  - `pdm run lint-fix` (pass)
  - `pdm run typecheck-all` (pass)
  - `pdm run pytest-root tests/sir_convert_a_lot -q` (pass; 167 passed, 7 skipped)
  - `pdm run validate-tasks` (pass)
  - `pdm run validate-docs` (pass)
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
