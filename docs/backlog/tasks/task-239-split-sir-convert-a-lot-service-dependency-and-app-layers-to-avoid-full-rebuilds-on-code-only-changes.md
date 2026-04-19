---
id: task-239-split-sir-convert-a-lot-service-dependency-and-app-layers-to-avoid-full-rebuilds-on-code-only-changes
title: Split Sir Convert-a-Lot service dependency and app layers to avoid full rebuilds on code-only changes
type: task
status: completed
priority: high
created: '2026-03-18'
last_updated: '2026-04-19'
related:
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md
labels:
  - docker
  - buildkit
  - devops
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Refactor the root service image so app-source-only updates reuse stable system
and dependency layers instead of rebuilding the entire HTTP service runtime on
every deploy.

This task is the completed partial layering slice. It narrowed the Docker build
context and app-source copy boundary. It did not separate runtime dependency
truth from full `pyproject.toml`; Task 255 owns that follow-up.

## PR Scope

- Replace the monolithic root `Dockerfile` with a layered service build.
- Keep the dependency layer stable across app-runtime source changes.
- Remove the redundant CUDA-torch install path from the service dependency
  build and install the ROCm torch stack directly.
- Preserve the existing single-service compose contract and `/readyz`
  revision semantics.

Out of scope for this task:

- separating dependency hash inputs from full `pyproject.toml`;
- introducing dedicated dependency image tags;
- proving PDM script-only changes are cache-hot.

Those boundaries are governed by Task 255.

## Deliverables

- [x] Layered root service `Dockerfile`
- [x] Filtered service requirements export helper for the dependency build
- [x] Contract tests that lock the new layering behavior
- [x] Verification notes for the aborted Hemma rebuild and cache cleanup

## Progress Notes

- 2026-03-18:
  - The dependency-builder now reads the canonical ROCm torch pins from
    `pyproject.toml` through a dedicated service-image build-contract helper,
    instead of duplicating those pins in `compose.yaml` and `Dockerfile`.
  - The final runtime layer no longer copies the whole `scripts/` tree; it now
    copies the minimal service runtime package surface plus `templates/`, which
    keeps unrelated ML/devops changes from invalidating the thin app layer.
  - The Hemma GPU runtime verifier no longer assumes `pdm` exists inside the
    service image and now probes the container with `python` directly.
  - The root `.dockerignore` now whitelists only the files and package
    subtrees that the service image actually copies, which keeps BuildKit from
    receiving large irrelevant repo sections such as `build/`, `docs/`,
    `tests/`, and unrelated script packages during code-only deploys.
- 2026-04-19:
  - Task 239 is retained as the partial layering slice that narrowed context
    and app-source invalidation, but it did not separate dependency truth from
    full `pyproject.toml`.
  - Task 255 now owns the follow-up dependency-image extraction: PDM
    script-only changes must not invalidate ROCm torch, EasyOCR preload, or
    other heavy dependency work.

## Acceptance Criteria

- [x] App-runtime source changes under the service package do not require the
  final runtime image to copy the entire `scripts/` tree.
- [x] The service dependency build no longer installs CUDA-flavoured torch
  packages only to uninstall them again before the ROCm install.
- [x] Compose still runs one canonical prod service with the same readiness
  lane and revision environment contract.
- [x] Automated tests cover the filtered requirements export and updated
  Docker/compose contract.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
