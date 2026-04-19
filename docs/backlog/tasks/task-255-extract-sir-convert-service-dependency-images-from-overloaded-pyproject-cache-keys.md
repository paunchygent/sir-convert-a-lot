---
id: task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys
title: Extract Sir Convert service dependency images from overloaded pyproject cache keys
type: task
status: completed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/tasks/task-239-split-sir-convert-a-lot-service-dependency-and-app-layers-to-avoid-full-rebuilds-on-code-only-changes.md
  - docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - Dockerfile
  - Dockerfile.local
  - compose.yaml
  - compose.local.yaml
  - pyproject.toml
  - pdm.lock
labels:
  - docker
  - buildkit
  - hemma
  - devops
  - production
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Close the remaining production image layering defect left after Task 239:
the service image now has a thinner app layer, but its heavy dependency stage
still treats full `pyproject.toml` as dependency truth. Because `pyproject.toml`
also contains PDM scripts, tool configuration, and repo metadata, a trivial
ops-surface change can invalidate the dependency-builder chain and force a
normal runtime dependency reinstall, ROCm torch reinstall/download, EasyOCR
model preload, `.venv` copy, and image export.

Make Sir Convert-a-Lot's service image behave more like HuleEdu's explicit
deps-image lane: dependency rebuilds must be deliberate and rare, while
source-only and ops-command-only changes stay cache-hot.

## PR Scope

- Define a narrow service dependency input contract that is separate from full
  repo metadata. The contract must include runtime dependency truth, ROCm/CPU
  runtime pins, and any EasyOCR preload inputs that truly affect the dependency
  image.
- Add or generate a stable service requirements artifact and runtime pins
  artifact so dependency image cache keys do not depend on PDM scripts, tool
  configuration, or unrelated `pyproject.toml` metadata.
- Add a dedicated dependency image lane for production ROCm builds, for
  example `sir-convert-a-lot-deps-rocm:<hash>`. Add a CPU/local dependency
  image lane only if it keeps the local Docker contract simpler than a shared
  mechanism with distinct pins.
- Update the runtime service image so it consumes the dependency image through
  an explicit `DEPS_IMAGE` build argument and copies only application/runtime
  source after dependencies are already baked.
- Add BuildKit cache mounts for package-manager downloads in dependency image
  builds. Do not use `--no-cache-dir` in a way that defeats the mounted pip
  cache for large ROCm wheels.
- Keep the current aggressive `.dockerignore` whitelist unless a specific
  dependency-image input requires widening it.
- Add command surfaces for explicit dependency-image builds and clean rebuilds.
  Production deploy/recreate commands must not rebuild dependency images unless
  the dependency hash changes or the operator explicitly asks for that work.
- Update compose contracts so production and local service builds pass the
  selected dependency image explicitly and keep the dev/prod split introduced
  by Task 254.
- Update the Hemma runbook with the dependency-image rebuild decision tree,
  cache-hot deploy expectations, and proof commands.

Out of scope:

- changing conversion API behavior;
- changing public-edge recovery semantics from Task 254;
- pruning Hemma BuildKit cache as part of normal proof, except when explicitly
  testing a cold dependency rebuild;
- moving Docker persistent state away from the existing Hemma storage contract.

## Deliverables

- [x] A committed dependency-image Dockerfile or equivalent build surface for
  the production ROCm dependency layer.
- [x] A committed narrow dependency input artifact or generator/validator pair
  for service runtime requirements and runtime pins.
- [x] Runtime service image build uses `DEPS_IMAGE` and no longer rebuilds
  heavy dependencies because full `pyproject.toml` changed for a PDM script or
  tooling-only reason.
- [x] BuildKit pip cache mounts are used for dependency package downloads,
  including ROCm torch wheel downloads.
- [x] Production/local compose and PDM command surfaces expose explicit
  dependency-image build, clean rebuild, and normal service rebuild paths.
- [x] Runbook guidance explains when to rebuild dependency images and how to
  prove a normal deploy stayed cache-hot.
- [x] Contract tests cover dependency hash inputs, Dockerfile layering,
  compose build arguments, and pyproject script-only non-invalidation.

## Progress Notes

- 2026-04-19:
  - Added `Dockerfile.deps` as the explicit ROCm/CPU dependency image build
    surface. It copies only generated `docker/service-deps/` inputs and uses
    BuildKit pip cache mounts for normal requirements, CPU torch, and ROCm
    torch installs.
  - Reduced `Dockerfile` and `Dockerfile.local` to runtime/app images that
    consume `DEPS_IMAGE` and copy application source only after `.venv`, torch,
    and EasyOCR models are already baked in a dependency image.
  - Added `scripts/devops/service-deps-image.sh` and PDM command surfaces:
    `prod-deps-rocm-build`, `prod-deps-rocm-build-clean`,
    `dev-deps-cpu-build`, while preserving normal `prod-build`,
    `prod-recreate`, and `dev-build` flows through dependency-image ensure.
  - Added `service_dependency_inputs.py` and generated
    `docker/service-deps/` artifacts. The dependency hash is computed from
    filtered production requirements, runtime pins, and EasyOCR preload inputs,
    not PDM scripts or tool-only config.
  - Local contract tests prove script-only `pyproject.toml` changes keep the
    dependency hash stable and runtime dependency/runtime pin changes move it.
  - Local gates passed: docs, skills, handoff, format, lint, typecheck,
    compose contract tests, service-image/compose/dockerfile test slice,
    coverage gate, task index, and whitespace diff check.
  - Detached Hemma proof ran from commit
    `7173c03f8b414caa7fa1e9c84a0c6b33b5b357b8`: the ROCm dependency image
    build installed ROCm torch and preloaded EasyOCR once, the app-only
    production build consumed that dependency image without rerunning heavy
    dependency work, and `prod-recreate` restarted `sir_convert_a_lot_prod`
    healthy.
  - Final durable proof artifacts are present under
    `build/verification/task-255-service-deps-image-cache/`.
  - Review 05 found that the first hash-tagged image identity could stay stale
    when the dependency-image build recipe changed. The fix adds a separate
    build-recipe hash and combined dependency-image hash, labels images with
    all three freshness values, and makes normal `ensure` reject existing tags
    whose labels do not match the current contract.

## Acceptance Criteria

- [x] A PDM script-only change to `pyproject.toml` does not change the service
  dependency hash and does not invalidate the ROCm dependency image layer.
- [x] A real runtime dependency or runtime pin change does change the service
  dependency hash and requires an explicit dependency-image rebuild.
- [x] A dependency-image recipe change changes the deploy-facing dependency
  image identity even when runtime package truth is unchanged.
- [x] The production runtime image consumes a dependency image through an
  explicit `DEPS_IMAGE` build argument and copies only app/runtime source after
  dependency layers are established.
- [x] ROCm torch and EasyOCR preload work are in the dependency image lane, not
  repeated during app-only service rebuilds.
- [x] BuildKit dependency builds reuse pip package cache across invalidated
  dependency-layer rebuilds unless the operator intentionally prunes cache.
- [x] `compose.yaml` and `compose.local.yaml` keep separate production/local
  surfaces and do not regress to the dev/prod compose confusion closed by
  Task 254.
- [x] Hemma verification demonstrates one dependency rebuild and one subsequent
  app-only or ops-only rebuild where the ROCm dependency work remains cached.
- [x] Existing dependency image tags are accepted only when Docker image labels
  match the current dependency hash, recipe hash, and dependency-image hash.

## Validation Commands

- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "service_image or compose or dockerfile" -q`
- `pdm run coverage-gate`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- `pdm run prod-deps-rocm-build`
- `pdm run prod-deps-rocm-build-clean`
- `pdm run prod-build`
- `pdm run prod-recreate sir_convert_a_lot_prod`
- `pdm run dev-deps-cpu-build`
- `pdm run dev-build`
- `pdm run run-local-pdm hemma-command-start task255-prod-deps-rocm-build -- pdm run prod-deps-rocm-build`
- `pdm run run-local-pdm hemma-command-monitor -- <remote-deps-build-log-path>`
- `pdm run run-local-pdm hemma-command-start task255-prod-app-only-build -- pdm run prod-build`
- `pdm run run-local-pdm hemma-command-monitor -- <remote-app-build-log-path>`
- `pdm run run-local-pdm hemma-command-start task255-prod-recreate -- pdm run prod-recreate sir_convert_a_lot_prod`
- `pdm run run-local-pdm hemma-command-monitor -- <remote-recreate-log-path>`
- `git diff --check`

The `prod-deps-rocm-build`, `prod-deps-rocm-build-clean`,
`dev-deps-cpu-build`, and `dev-build` surfaces are deliverables for this task.
If the final command names change during implementation, update this task,
compose contracts, and the runbook in the same slice before claiming
validation.

Hemma proof commands must run through detached command surfaces when they can
outlive a local terminal session. The live proof must capture these artifacts
under `build/verification/task-255-service-deps-image-cache/`:

- `dependency-inputs-before.json`: selected dependency input files, runtime
  pins, and computed dependency hash before the script-only change.
- `dependency-inputs-after-script-only.json`: same payload after a PDM
  script-only change, proving the dependency hash is unchanged.
- `dependency-inputs-after-runtime-dependency.json`: controlled runtime
  dependency or runtime pin delta proving the hash changes when dependency
  truth changes.
- `prod-deps-rocm-build.log`: detached dependency image build log proving the
  ROCm dependency image tag and pip cache mount behavior.
- `prod-deps-rocm-build-clean.log`: optional detached clean dependency image
  rebuild log for explicit cold dependency rebuild testing only.
- `prod-app-only-build.log`: detached app/ops-only service image rebuild log
  proving ROCm torch and EasyOCR preload work are cached or not rerun.
- `image-tags.json`: dependency image tag, runtime image tag, revision, and
  dependency hash, recipe hash, and dependency-image hash used for the proof.
- `buildkit-cache-summary.txt`: non-destructive BuildKit cache summary before
  and after the proof.
- `report.md` / `report.json`: final pass/fail summary for dependency hash,
  cache-hot rebuild, compose surface, and Hemma detached monitoring evidence.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
