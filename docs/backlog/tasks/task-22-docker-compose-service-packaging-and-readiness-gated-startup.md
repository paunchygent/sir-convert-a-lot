---
id: task-22-docker-compose-service-packaging-and-readiness-gated-startup
title: Docker compose service packaging and readiness-gated startup
type: task
status: completed
priority: high
created: '2026-02-16'
last_updated: '2026-02-16'
related:
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/tasks/task-19-fastapi-lifecycle-and-readiness-contract-replacing-script-band-aids.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - docker
  - compose
  - readiness
  - fastapi
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Package the Task 19 FastAPI lifecycle/readiness contract into canonical Docker images and
Compose startup semantics so prod/eval services are reproducible and fail-closed.

## PR Scope

- Add or harden Docker build surfaces for service runtime (prod/eval compatible).
- Add Compose definitions for service startup with explicit health/readiness strategy.
- Ensure service startup wiring keeps `service.py`/`service_eval.py` profile invariants.
- Keep startup checks app-driven (`/readyz`) rather than ad hoc shell-only guards.

Out of scope:

- persistence retention/recovery internals (Task 23),
- operator runbook expansion and Hemma deployment checklist finalization (Task 24).

## Decision Lock

1. Compose standard:
   - Use `docker compose` v2 only.
   - No `docker-compose` legacy command surface.
1. Startup correctness:
   - Container health checks must use `/readyz` (not `/healthz`).
   - Readiness remains fail-closed for revision/profile/data-root mismatches.
1. Lane isolation:
   - prod and eval run as separate services with explicit profile entrypoints.
   - prod/eval data roots must be isolated by compose configuration.
1. Command governance:
   - Canonical local execution uses committed scripts + PDM script surfaces.
   - No ad hoc operational command variants in runbook examples.
1. Out-of-scope enforcement:
   - Retention/recovery semantics stay in Task 23.
   - Hemma operations close-out stays in Task 24.

## Skriptoteket-Aligned Compose Conventions (Scaled)

Use Skriptoteket operational shape as baseline, reduced to this service's smaller scope:

1. Service topology:
   - two HTTP services only: `sir_convert_a_lot_prod`, `sir_convert_a_lot_eval`,
   - no extra worker/frontend/database services in this slice.
1. Restart policy:
   - both services use `restart: unless-stopped`.
1. Environment wiring:
   - use `env_file` plus explicit `environment` overrides for deterministic profile/data-root/revision contract values,
   - keep secret/env source externalized through `.env` and wrapper flow.
1. Persistence wiring:
   - use named volumes for prod/eval data roots (separate volumes per lane),
   - do not use bind mounts for canonical runtime persistence in this slice.
1. Health checks:
   - use container healthchecks that call `/readyz` on each lane listener,
   - use deterministic interval/timeout/retry/start-period values.
1. Naming and operability:
   - explicit `container_name` values matching lane role,
   - compose debugging flow must always include:
     - `docker compose ps`,
     - `docker compose logs --tail=200 <service>`,
     - `docker compose config`.
1. Network scope:
   - default internal compose network unless a concrete cross-stack integration need is documented in-task.

## Execution Plan

1. Add container build artifacts:
   - create canonical `Dockerfile` and `.dockerignore`,
   - ensure runtime entry remains `service.py` / `service_eval.py` compatible.
1. Add compose topology:
   - create `compose.yaml` with prod/eval services,
   - wire deterministic env vars for `service_profile`, expected revision, and data roots,
   - add health checks using `/readyz`,
   - apply scaled Skriptoteket conventions for restart/env_file/named-volumes/container naming.
1. Add deterministic script surfaces:
   - add `scripts/devops` helpers for compose up/down/restart/status/logs,
   - expose via `pyproject.toml` PDM scripts.
1. Add focused tests:
   - compose contract tests for healthcheck path, lane isolation env, and service commands,
   - regression tests for readiness behavior under compose-configured mismatch cases.
1. Update docs:
   - runbook references to canonical compose commands,
   - API docs only if runtime contract fields or semantics change.
1. Run full quality/docs gates and record evidence in task + current log.

## Risks and Mitigations

- Risk: health checks accidentally probe `/healthz` and mask misconfiguration.
  Mitigation: assert `/readyz` usage in compose contract tests.
- Risk: prod/eval data-root collision in compose env wiring.
  Mitigation: explicit separate env vars + automated config assertions.
- Risk: ad hoc compose commands drift from runbook.
  Mitigation: committed PDM script surfaces used as canonical examples.

## Deliverables

- [x] Canonical Docker build surface for the PDF-to-MD service runtime.
- [x] Compose service definitions for prod/eval lanes with deterministic env mapping.
- [x] Readiness-aware startup/health flow that aligns with Task 19 contract.
- [x] Focused integration/regression tests for container startup and readiness behavior.

## Acceptance Criteria

- [x] `docker compose` startup yields healthy containers only when `/readyz` is ready.
- [x] Stale revision or profile/data-root mismatch yields deterministic non-ready behavior.
- [x] Compose configuration is reproducible and documented without ad hoc command variants.
- [x] Local quality/docs gates remain green after packaging changes.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation and Evidence (2026-02-16)

- Container packaging surfaces added:
  - `Dockerfile`
  - `.dockerignore`
- Compose topology added with prod/eval lane isolation:
  - `compose.yaml`
  - `/readyz` healthchecks on `8085`/`8086`
  - named volumes: `sir-convert-a-lot-prod-data`, `sir-convert-a-lot-eval-data`
  - optional `env_file` contract (`.env`, `required: false`) + explicit deterministic env wiring.
- Canonical compose command surface added:
  - `scripts/devops/dev-compose.sh`
  - PDM scripts in `pyproject.toml` (`dev-start`, `dev-stop`, `dev-build`, `dev-build-clean`,
    `dev-recreate`, `dev-logs`, `dev-ps`, `dev-config`, `dev-check`)
  - wrapper now auto-derives `SIR_CONVERT_A_LOT_SERVICE_REVISION` from repo `HEAD` and
    defaults `SIR_CONVERT_A_LOT_EXPECTED_REVISION` to the same value when unset.
- Contract/regression coverage added:
  - `tests/sir_convert_a_lot/test_compose_contract.py`
  - `tests/sir_convert_a_lot/test_dev_compose_wrapper.py`
  - existing readiness mismatch semantics remain covered in
    `tests/sir_convert_a_lot/test_api_contract_v1.py`.
- Docker build/runtime bugfix applied during live compose probe:
  - `Dockerfile` now uses supported `pdm sync --prod --no-editable --no-self`
    args for pinned `pdm==2.26.4` (removed unsupported `--frozen-lockfile`).
- Runbook sync:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md` now documents the canonical compose wrapper flow.
- Operational smoke evidence:
  - `pdm run dev-start` (pass; built images and started both services).
  - `pdm run dev-ps` (pass; both services reached `healthy`).
  - `curl -fsS http://127.0.0.1:8085/readyz` (pass; `status="ready"`).
  - `curl -fsS http://127.0.0.1:8086/readyz` (pass; `status="ready"`).
  - `pdm run dev-stop` (pass; compose stack torn down cleanly).
  - `pdm run dev-config` (pass; resolved compose config with revision defaults).
  - `pdm run dev-check` (pass; compose config+ps probe).
- Full gates:
  - `pdm run format-all`
  - `pdm run lint-fix`
  - `pdm run typecheck-all`
  - `pdm run pytest-root tests/sir_convert_a_lot -q`
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
