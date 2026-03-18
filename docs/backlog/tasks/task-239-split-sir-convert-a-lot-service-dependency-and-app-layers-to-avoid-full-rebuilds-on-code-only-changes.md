---
id: task-239-split-sir-convert-a-lot-service-dependency-and-app-layers-to-avoid-full-rebuilds-on-code-only-changes
title: Split Sir Convert-a-Lot service dependency and app layers to avoid full rebuilds on code-only changes
type: task
status: proposed
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

- [ ] Layered root service `Dockerfile`
- [ ] Filtered service requirements export helper for the dependency build
- [ ] Contract tests that lock the new layering behavior
- [ ] Verification notes for the aborted Hemma rebuild and cache cleanup

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

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
