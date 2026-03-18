---
id: task-239-split-sir-convert-a-lot-service-dependency-and-app-layers-to-avoid-full-rebuilds-on-code-only-changes
title: Split Sir Convert-a-Lot service dependency and app layers to avoid full rebuilds on code-only changes
type: task
status: active
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related: []
labels: []
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Refactor the root service image so code-only updates reuse stable system and
dependency layers instead of rebuilding the entire HTTP service runtime on
every deploy.

## PR Scope

- Replace the monolithic root `Dockerfile` with a layered service build.
- Keep the dependency layer stable across `scripts/`-only changes.
- Remove the redundant CUDA-torch install path from the service dependency
  build and install the ROCm torch stack directly.
- Preserve the existing single-service compose contract and `/readyz`
  revision semantics.

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

## Acceptance Criteria

- [ ] Code-only changes under `scripts/` do not invalidate the heavy dependency
  layer in the root service image.
- [ ] The service dependency build no longer installs CUDA-flavoured torch
  packages only to uninstall them again before the ROCm install.
- [ ] Compose still runs one canonical prod service with the same readiness
  lane and revision environment contract.
- [ ] Automated tests cover the filtered requirements export and updated
  Docker/compose contract.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
