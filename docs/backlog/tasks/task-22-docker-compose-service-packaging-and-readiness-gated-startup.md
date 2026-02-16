---
id: task-22-docker-compose-service-packaging-and-readiness-gated-startup
title: Docker compose service packaging and readiness-gated startup
type: task
status: proposed
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

## Deliverables

- [ ] Canonical Docker build surface for the PDF-to-MD service runtime.
- [ ] Compose service definitions for prod/eval lanes with deterministic env mapping.
- [ ] Readiness-aware startup/health flow that aligns with Task 19 contract.
- [ ] Focused integration/regression tests for container startup and readiness behavior.

## Acceptance Criteria

- [ ] `docker compose` startup yields healthy containers only when `/readyz` is ready.
- [ ] Stale revision or profile/data-root mismatch yields deterministic non-ready behavior.
- [ ] Compose configuration is reproducible and documented without ad hoc command variants.
- [ ] Local quality/docs gates remain green after packaging changes.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
