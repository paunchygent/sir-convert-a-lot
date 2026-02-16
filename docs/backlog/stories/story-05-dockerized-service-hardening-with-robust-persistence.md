---
id: story-05-dockerized-service-hardening-with-robust-persistence
title: Dockerized service hardening with robust persistence
type: story
status: proposed
priority: high
created: '2026-02-16'
last_updated: '2026-02-16'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-19-fastapi-lifecycle-and-readiness-contract-replacing-script-band-aids.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - docker
  - persistence
  - devops
  - reliability
---

Implementation slice with acceptance-driven scope.

## Objective

Define and deliver the next architecture slice after Task 19: a reproducible Docker-first
service runtime with strict readiness gating and durable persistence semantics for prod/eval
lanes on Hemma.

## Scope

- Package the FastAPI service into deterministic Docker images and Compose surfaces.
- Enforce startup/readiness flow so traffic is only served when revision/profile/data-root
  invariants are valid.
- Introduce explicit durable persistence layout and retention/recovery guarantees for
  containerized operation.
- Publish canonical runbook/deploy verification flow for Hemma that remains GPU-first and
  fail-closed.

## Acceptance Criteria

1. Dockerized prod/eval service startup is deterministic and uses canonical compose commands.
1. Readiness-gated startup prevents stale/misconfigured lanes from being treated as healthy.
1. Container restarts preserve in-flight/finished job artifacts per defined retention policy.
1. Operators can deploy, verify, and recover using documented, script-backed commands only.
1. Evidence exists for local + Hemma validation across startup, readiness, persistence,
   and recovery paths.

## Test Requirements

- Container startup/restart integration tests for readiness and persistence behavior.
- Regression tests for retention/recovery semantics in containerized data roots.
- Runbook-level smoke validation with explicit Hemma command evidence.

## Done Definition

Story is complete when Tasks 22-24 are completed with validation evidence and linked
runbook/API documentation updates.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
