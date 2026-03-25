---
id: 'task-250-add-a-cpu-only-local-docker-dev-profile-for-macbook-service-debugging'
title: 'Add a CPU-only local Docker dev profile for MacBook service debugging'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-25'
last_updated: '2026-03-25'
related:
  - docs/backlog/tasks/task-27-dockerized-hemma-rocm-gpu-passthrough-and-runtime-wheel-pinning.md
  - docs/backlog/tasks/task-239-split-sir-convert-a-lot-service-dependency-and-app-layers-to-avoid-full-rebuilds-on-code-only-changes.md
  - docs/converters/sir_convert_a_lot.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - docker
  - local-dev
  - cpu
  - runtime
  - service
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add an explicit CPU-only local Docker development profile for the Sir
Convert-a-Lot v2 service so laptop debugging on the MacBook does not depend on
the Hemma ROCm image contract.

This local profile is not meant to replace the Hemma production lane. The
policy remains:

- Hemma GPU/prod is the default real integration lane.
- local `:8085` is opt-in debug infrastructure only.

The goal is to make that opt-in local lane deterministic, Dockerized, and
fast enough for HTML-to-PDF and other non-ROCm debugging workflows without
teaching downstream repos to rely on host-run `uvicorn` processes.

## PR Scope

- Add a dedicated local compose surface separate from the canonical Hemma/prod
  `compose.yaml` contract.
- Add a CPU-specific Docker build that installs standard CPU torch wheels
  instead of ROCm wheels.
- Add a dedicated local service entrypoint/profile so health metadata can
  distinguish the local CPU lane from the production lane.
- Repoint local dev helper commands (`pdm run dev-start`, etc.) to the local
  CPU compose surface.
- Document that the local CPU Docker lane is opt-in debugging only and that
  Hemma/public remains the default downstream integration path.

Out of scope:

- changing the Hemma production `compose.yaml` service contract;
- changing the public service URL policy (`127.0.0.1:28085` tunnel or
  `https://convert.hule.education`);
- introducing any host-run `uvicorn` support as a valid local integration path;
- broad conversion-runtime refactors beyond the local CPU build contract.

## Deliverables

- [ ] `compose.local.yaml` defines a CPU-only local Docker service.
- [ ] `Dockerfile.local` builds without ROCm runtime wheel assumptions.
- [ ] `pdm run dev-start` and related local helper commands use the local CPU
  compose surface instead of the Hemma/prod compose file.
- [ ] docs and skills state that Hemma/public is still the default downstream
  integration lane and that local `:8085` is explicit debug-only infrastructure.
- [ ] focused contract tests protect the new local compose/build surface.

## Acceptance Criteria

- [ ] `docker compose -f compose.local.yaml config` succeeds locally.
- [ ] the local compose service does not declare ROCm devices or `video` /
  `render` passthrough.
- [ ] the local Dockerfile installs CPU torch pins instead of ROCm wheel pins.
- [ ] the local service entrypoint reports a distinct local CPU service profile.
- [ ] existing `compose.yaml` production contract assertions remain valid.
- [ ] local docs explicitly forbid host-run `uvicorn` as the sanctioned local
  integration path.

## Checklist

- [ ] add the local CPU compose and Dockerfile surfaces
- [ ] keep `compose.yaml` and the Hemma ROCm lane unchanged
- [ ] extend the build contract helpers and focused tests
- [ ] update the local dev docs/skills to point at the CPU Docker lane
- [ ] rerun focused tests, docs validation, and local compose verification
