---
id: review-05-ruthless-review-of-task-255-dependency-image-cache-split
title: Ruthless review of Task 255 dependency image cache split
type: review
status: completed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - Dockerfile
  - Dockerfile.local
  - Dockerfile.deps
  - docker/service-deps/service-requirements.txt
  - scripts/devops/compose-actions.sh
  - scripts/devops/service-deps-image.sh
  - scripts/sir_convert_a_lot/devops/export_service_requirements.py
  - scripts/sir_convert_a_lot/devops/service_dependency_inputs.py
  - tests/sir_convert_a_lot/test_service_dependency_inputs.py
  - tests/sir_convert_a_lot/test_compose_contract.py
  - tests/sir_convert_a_lot/test_local_compose_contract.py
  - build/verification/service-dependency-image-cache/report.md
  - build/verification/service-dependency-image-cache/report.json
labels:
  - review
  - task-255
  - devops
  - hemma
  - docker
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Reviewed commits:
  - `7173c03f8b414caa7fa1e9c84a0c6b33b5b357b8` - Task 255 implementation.
  - `194cfb0` - final Hemma proof artifacts and docs closeout.
  - `d23855375ec848a8c45ae40d43e23c4f8b23d319` - recipe-hash freshness fix.
- Governing authority:
  `docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md`.
- Public surfaces under review:
  - Production and local Dockerfiles consuming `DEPS_IMAGE`.
  - Dependency image Dockerfile and generated `docker/service-deps/` inputs.
  - PDM command surfaces for `prod-deps-rocm-build`,
    `prod-deps-rocm-build-clean`, `dev-deps-cpu-build`, `prod-build`,
    `prod-recreate`, and local equivalents.
  - Hemma proof artifacts under
    `build/verification/service-dependency-image-cache/`.
- Compatibility posture:
  - Clean DevOps contract change. Existing callers should use the documented
    PDM wrappers; no legacy Dockerfile dependency-builder shim is required.
  - Normal app-only deploys must stay cache-hot, but dependency-image
    freshness must fail closed when dependency-image build truth changes.
- Third-party/library check:
  - Context7 Docker docs confirm `RUN --mount=type=cache` for pip and split
    dependency inputs are modern BuildKit cache patterns.
- Validation evidence gathered:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_service_dependency_inputs.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py -q`:
    pass, `28 passed`.
  - Follow-up local gates passed after the fix: docs, skills, handoff, format,
    lint, typecheck, compose contract tests, service-image/compose/dockerfile
    slice, coverage gate, task index, and whitespace diff check.
  - Follow-up detached Hemma proof passed from commit
    `d23855375ec848a8c45ae40d43e23c4f8b23d319`: recipe-aware dependency image
    `sir-convert-a-lot-deps-rocm:b6265e4ee42c43c255e400bc1516cc04d8601ceaf6961008dc09ad7a60f6df89`
    was labeled with matching dependency, recipe, and dependency-image hashes;
    the subsequent app-only build reused it without rerunning ROCm torch or
    EasyOCR work; production recreate finished healthy.

## Findings

1. `high` - Hash-tagged dependency images can stay stale when the dependency
   build recipe changes.

   - Evidence:
     `scripts/sir_convert_a_lot/devops/service_dependency_inputs.py` lines
     98-115 compute the dependency hash from filtered requirements, runtime
     kind, runtime pins, schema version, and EasyOCR preload fields only.
     `scripts/devops/service-deps-image.sh` lines 100-103 then treats the
     existing `sir-convert-a-lot-deps-<runtime>:<dependency_hash>` tag as
     sufficient freshness proof and skips `Dockerfile.deps` entirely on normal
     `ensure`. The hash omits `Dockerfile.deps` itself, the `PYTHON_IMAGE`
     value, apt package list, pip upgrade policy, BuildKit frontend version,
     and the dependency-image helper implementation that controls those build
     steps.
   - Why it matters:
     A future change to `Dockerfile.deps`, the base image policy, system
     packages, pip install flags, or EasyOCR preload command can be merged and
     deployed through the normal `prod-build` / `prod-recreate` wrapper while
     `ensure` silently reuses an older dependency image with the same
     requirements/runtime-pin hash. That breaks the core Task 255 promise that
     the explicit dependency image is the current runtime dependency truth, and
     it is especially risky because `Dockerfile.deps` currently installs
     mutable inputs such as `python:3.11-slim` and unpinned upgraded pip under
     the same dependency hash.
   - Required fix:
     Make the dependency-image identity cover the full dependency build
     contract, not only Python package truth. Include a stable build-recipe
     digest in the payload, for example hashes of `Dockerfile.deps`,
     `scripts/devops/service-deps-image.sh`, and the dependency-input generator
     code plus explicit `PYTHON_IMAGE` and system package contract fields. Then
     have `ensure` verify the existing image label(s) against both the
     dependency hash and recipe hash before accepting a tag. If the repo
     deliberately wants a narrower package-only hash, add a separate
     `recipe_hash` tag/label and use both values for freshness.
   - Proof requirement:
     Add a contract test that mutates only the dependency build recipe or base
     image contract and proves `ensure` no longer accepts the old dependency
     image identity. Add a wrapper/unit test for label verification, then run:
     `pdm run pytest-root tests/sir_convert_a_lot/test_service_dependency_inputs.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py -q`.

## Decision

changes_requested

## Response

The implementation is strong on the app/dependency split and the Hemma proof
shows the happy path. It is not approval-ready because the image identity used
by normal deploys is narrower than the actual dependency-image build contract.

## Resolution

Resolved on 2026-04-19. The follow-up keeps the runtime package
`dependency_hash` narrow, adds a separate build-recipe hash from
`Dockerfile.deps`, `scripts/devops/service-deps-image.sh`, the dependency input
generator, explicit `PYTHON_IMAGE`, system packages, pip policy, BuildKit cache
mount IDs, and EasyOCR preload command contract, then derives a combined
dependency-image hash for image tags. Dependency images are labeled with all
three hashes, and normal `ensure` now verifies those labels before reusing an
existing image tag.

## Follow-up Actions

1. Completed: re-run the focused local tests and repeat a Hemma app-only proof after the
   recipe-hash fix to show unchanged app code still stays cache-hot.
1. Completed: update the Task 255 proof packet with recipe hash, combined image identity,
   and detached Hemma proof evidence.

## Completion

Initial review completed on 2026-04-19 with changes requested. Follow-up
completed on 2026-04-19 and the finding is resolved.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
