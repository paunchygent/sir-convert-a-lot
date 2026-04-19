---
id: story-05-dockerized-service-hardening-with-robust-persistence
title: Dockerized service hardening with robust persistence
type: story
status: in_progress
priority: high
created: '2026-02-16'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-19-fastapi-lifecycle-and-readiness-contract-replacing-script-band-aids.md
  - docs/backlog/tasks/task-22-docker-compose-service-packaging-and-readiness-gated-startup.md
  - docs/backlog/tasks/task-23-durable-persistence-layout-retention-and-recovery-for-containerized-runtime.md
  - docs/backlog/tasks/task-24-container-operations-runbook-and-hemma-deployment-verification-for-dockerized-service.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/backlog/tasks/task-239-split-sir-convert-a-lot-service-dependency-and-app-layers-to-avoid-full-rebuilds-on-code-only-changes.md
  - docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md
  - docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - docker
  - buildkit
  - persistence
  - devops
  - hemma
  - reliability
---

Implementation slice with acceptance-driven scope.

## Objective

Define and deliver the Docker-first service operations architecture for the
Hemma-hosted conversion service: reproducible images, explicit dependency
image lanes, strict readiness gating, durable persistence semantics, detached
production deploys, and durable verification artifacts for prod/eval lanes on
Hemma.

## Scope

- Package the FastAPI service into deterministic Docker images and Compose surfaces.
- Keep dependency image rebuilds explicit and rare by separating dependency
  truth from repo metadata and app/runtime source.
- Enforce startup/readiness flow so traffic is only served when revision/profile/data-root
  invariants are valid.
- Introduce explicit durable persistence layout and retention/recovery guarantees for
  containerized operation.
- Publish canonical runbook/deploy verification flow for Hemma that remains
  GPU-first, detached for long-running production work, and fail-closed at the
  public edge.

## Acceptance Criteria

1. Dockerized prod/eval service startup is deterministic and uses canonical compose commands.
1. Dependency-image rebuilds are keyed by narrow dependency artifacts, not by
   full `pyproject.toml` metadata or PDM script changes.
1. Readiness-gated startup prevents stale/misconfigured lanes from being treated as healthy.
1. Container restarts preserve in-flight/finished job artifacts per defined retention policy.
1. Operators can deploy, verify, and recover using documented, script-backed commands only.
1. Long-running Hemma production deploy/recover work is detached and monitored separately.
1. Evidence exists for local + Hemma validation across startup, readiness,
   persistence, public-edge recovery, cache-hot rebuild, and recovery paths.

## Test Requirements

- Container startup/restart integration tests for readiness and persistence behavior.
- Regression tests for retention/recovery semantics in containerized data roots.
- Dockerfile/compose contract tests for dependency-image layering, dev/prod
  compose split, and cache-key input boundaries.
- Runbook-level smoke validation with explicit Hemma command evidence.

## Done Definition

Story is complete when Tasks 22-24 establish the base container runtime,
Task 254 proves detached production recovery/public-edge verification, and
Task 255 proves cache-hot dependency-image rebuild behavior with linked
runbook/API documentation updates.

## Progress Notes

- 2026-04-19: Task 255 completed the cache-hot dependency-image rebuild slice.
  Final evidence is in
  `build/verification/task-255-service-deps-image-cache/`. Story 05 remains
  open while Task 254 public-edge detached deploy verification is still the
  immediate production recovery authority.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
