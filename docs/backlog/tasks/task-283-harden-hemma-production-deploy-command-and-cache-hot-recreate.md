---
id: task-283-harden-hemma-production-deploy-command-and-cache-hot-recreate
title: Harden Hemma production deploy command and cache-hot recreate
type: task
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - hemma
  - deploy
  - docker
  - buildkit
  - dependency-cache
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the brittle Hemma production recreate invocation with one stable local
operator command and preserve the dependency-image cache contract for ordinary
code-only deploys.

The immediate production deploy exposed two command-surface problems:

- non-sudo remote `prod-recreate` can fail on the Docker socket;
- sudo can drop both `/home/paunchygent/.local/bin` for PDM and `/snap/bin` for
  Docker unless the operator hand-writes the environment bridge.

This task makes that bridge a named repo command and aligns
`hemma-deploy-and-verify` with it.

## PR Scope

- Add `pdm run hemma-prod-recreate` as the stable local command for recreating
  `sir_convert_a_lot_prod` and `sir_convert_a_lot_public_reserved` on Hemma.
- Preserve PDM, Docker, and BuildKit command discovery across the remote sudo
  boundary without requiring ad hoc operator command strings.
- Keep the lower-level `prod-recreate` compose wrapper as the canonical remote
  implementation.
- Keep dependency-image churn limited to changes in service requirements,
  runtime pins, `Dockerfile.deps`, or dependency-image recipe inputs.
- Add a regression test proving app/runtime Dockerfile changes do not alter the
  dependency-image recipe hash.

## Deliverables

- PDM command surface: `pdm run hemma-prod-recreate [service...]`.
- Shared sudo/PATH bridge in the stable command and `hemma-deploy-and-verify`
  fallback path.
- Regression coverage for dependency-image recipe stability on app/runtime
  Dockerfile changes.
- Runbook update that points operators to the stable command before lower-level
  command forms.

## Checklist

- [x] Implement the stable local Hemma production recreate command.
- [x] Align the deploy-and-verify sudo fallback with the stable command's
  PDM/Docker PATH bridge.
- [x] Preserve BuildKit and dependency-image ensure semantics through the
  existing compose wrapper.
- [x] Add focused regression coverage for cache-key boundaries.
- [x] Update runbook and active handoff pointers.

## Acceptance Criteria

- [x] Operators can run one stable command:
  `pdm run hemma-prod-recreate`.
- [x] The command defaults to recreating both the production service and the
  reserved public-edge service.
- [x] The command preserves `/home/paunchygent/.local/bin` and `/snap/bin`
  across sudo so remote PDM and Docker are found deterministically.
- [x] `hemma-deploy-and-verify` uses the same sudo/PATH fallback shape.
- [x] App/runtime Dockerfile changes do not move the dependency-image recipe
  hash.
- [x] The runbook points operators to the stable command before lower-level
  detached command forms.

## Validation

- `pdm run pytest-root tests/sir_convert_a_lot/test_service_dependency_inputs.py -q`
- `pdm run hemma-prod-recreate --help`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
