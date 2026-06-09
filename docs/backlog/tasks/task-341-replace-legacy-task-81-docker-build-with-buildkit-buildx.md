---
id: task-341-replace-legacy-task-81-docker-build-with-buildkit-buildx
title: Replace legacy Task 81 Docker build with BuildKit buildx
type: task
status: completed
priority: medium
created: '2026-05-30'
last_updated: '2026-05-30'
related:
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-84-remediate-task-81-openvoice-benchmark-root-causes-and-evidence-export.md
  - scripts/sir_convert_a_lot/devops/openvoice_benchmark_runtime.py
labels:
  - docker
  - buildkit
  - hemma
  - devops
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the remaining executable legacy `docker build` invocation from the
Task 81 OpenVoice benchmark lane and make the sidecar image build use
`docker buildx build --load`.

## PR Scope

- Change only the Task 81 OpenVoice sidecar image build command.
- Preserve existing image tags, Dockerfile selection, and build trigger
  semantics.
- Add a focused test proving the emitted Docker command uses BuildKit/buildx
  rather than legacy `docker build`.

## Deliverables

- [x] Task 81 runtime uses `docker buildx build --load`.
- [x] Focused Task 81 test covers the build command.

## Acceptance Criteria

- [x] No executable `docker build` invocation remains in the Task 81 runtime.
- [x] Existing Task 81 benchmark helper behavior remains otherwise unchanged.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation

- Red-first focused test:
  `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_openvoice_benchmark.py::test_ensure_image_present_builds_with_buildkit_buildx_load -q`
  failed while Task 81 still emitted legacy `docker build`.
- Focused proof:
  `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_openvoice_benchmark.py::test_ensure_image_present_builds_with_buildkit_buildx_load -q`
  passed after the runtime switched to `docker buildx build --load`.
- Cross-repo scan for executable/plain build examples no longer finds active
  legacy build commands; remaining matches are policy prohibitions, historical
  review text, guard assertions, or `docker builder prune`.
