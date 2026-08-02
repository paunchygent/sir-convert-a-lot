---
type: story
id: ST-SIRCON-01-05
title: Dockerized service hardening with robust persistence
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-01
links:
  decisions: []
acceptance_criteria:
- Dockerized prod/eval service startup is deterministic and uses canonical compose
  commands.
- Dependency-image rebuilds are keyed by narrow dependency artifacts, not full pyproject
  metadata or PDM script changes.
- Readiness-gated startup prevents stale or misconfigured lanes from being treated
  as healthy.
- Container restarts preserve in-flight and finished job artifacts per the defined
  retention policy.
- Operators can deploy, verify, and recover using documented script-backed commands
  only.
- Long-running Hemma production deploy and recovery work is detached and monitored
  separately.
- Evidence exists for local and Hemma validation across startup, readiness, persistence,
  public-edge recovery, cache-hot rebuild, and recovery paths.
retired_ids:
- story-05-dockerized-service-hardening-with-robust-persistence
---


## Context

State the actor or consumer need and the parent epic outcome this story serves.

## Epic Contract Slice

Define one independently reviewable observable behavior or capability slice.

## ADR Coverage

No new governing direction is introduced by this contract.

Applicable ADR IDs must equal the unique IDs in `links.decisions`; this section
records semantic coverage only and does not enforce readiness.

## Contract Inputs

- Accepted ADRs, references, runbooks, reviews, or prior backlog contracts that
  constrain this story.

## Live Verification Plan

- Story checkpoint and applicable acceptance criteria.
- Real route and expected observable result.
- Task evidence consumed and retained story-level verification evidence.

## Non-Goals

- Adjacent behavior or implementation work this story must not absorb.

## Notes

Record current story-local interpretation that does not belong in the contract,
ledger, or non-goals.

## Decision And Assumption Ledger

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

## Plan Document Review

Record findings, evidence, permitted next step, and residual risk. The
`readiness_review` frontmatter mapping is the machine authority for gate status.

## Story Closeout Review

Record verification result, evidence, permitted next step, unavailable mandatory
evidence, and residual risk. The `closeout_review` frontmatter mapping is the
machine authority for gate status and approval evidence.

## Source Body Preservation

Implementation slice with acceptance-driven scope.
## Objective
Define and deliver the Docker-first service operations architecture for the Hemma-hosted conversion service: reproducible images, explicit dependency image lanes, strict readiness gating, durable persistence semantics, detached production deploys, and durable verification artifacts for prod/eval lanes on Hemma.
## Scope
- Package the FastAPI service into deterministic Docker images and Compose surfaces.
- Keep dependency image rebuilds explicit and rare by separating dependency
truth from repo metadata and app/runtime source.
- Enforce startup/readiness flow so traffic is only served when revision/profile/data-root
invariants are valid.
- Introduce explicit durable persistence layout and retention/recovery guarantees for
containerized operation.
- Publish canonical runbook/deploy verification flow for Hemma that remains
GPU-first, detached for long-running production work, and fail-closed at the public edge.
## Acceptance Criteria
1. Dockerized prod/eval service startup is deterministic and uses canonical compose commands. 1. Dependency-image rebuilds are keyed by narrow dependency artifacts, not by full `pyproject.toml` metadata or PDM script changes. 1. Readiness-gated startup prevents stale/misconfigured lanes from being treated as healthy. 1. Container restarts preserve in-flight/finished job artifacts per defined retention policy. 1. Operators can deploy, verify, and recover using documented, script-backed commands only. 1. Long-running Hemma production deploy/recover work is detached and monitored separately. 1. Evidence exists for local + Hemma validation across startup, readiness, persistence, public-edge recovery, cache-hot rebuild, and recovery paths.
## Test Requirements
- Container startup/restart integration tests for readiness and persistence behavior.
- Regression tests for retention/recovery semantics in containerized data roots.
- Dockerfile/compose contract tests for dependency-image layering, dev/prod
compose split, and cache-key input boundaries.
- Runbook-level smoke validation with explicit Hemma command evidence.
## Done Definition
Story is complete when Tasks 22-24 establish the base container runtime, Task 254 proves detached production recovery/public-edge verification, and Task 255 proves cache-hot dependency-image rebuild behavior with linked runbook/API documentation updates.
## Progress Notes
- 2026-04-19: Task 255 completed the cache-hot dependency-image rebuild slice.
Final evidence is in `build/verification/service-dependency-image-cache/`. Story 05 remains open while Task 254 public-edge detached deploy verification is still the immediate production recovery authority.
## Checklist
- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized

