---
type: story
id: ST-SIRCON-06-03
title: Preserve internal service and local operator Sir Convert lanes
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-06
links:
  decisions: []
acceptance_criteria:
- Internal backend callers have a documented direct lane that does not require browser
  Gateway routing.
- Direct internal callers use the Sir Convert `InternalIdentityContextV1` authorization
  profile for job and artifact authorization.
- Local operator tunnel lane remains documented and tested.
- Operator credentials are explicit and never persisted in reports.
- GPU-backed conversion proof still works through the local lane.
- Docs no longer confuse direct local, internal, and public lanes.
retired_ids:
- story-35-preserve-internal-service-and-local-operator-sir-convert-lanes
---

## Context

## Epic Contract Slice

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review

## Historical Source Content

Implementation slice with acceptance-driven scope.

### Objective

Preserve Sir Convert as a direct internal Hemma network resource and local
operator GPU-offload service after product/browser access moves behind Gateway.

### Scope

- Document sanctioned internal service-to-service access.
- Require the Sir Convert `InternalIdentityContextV1` authorization profile
  for internal and operator job ownership, status reads, and artifact access.
- Preserve local tunnel/CLI workflows for heavy conversions.
- Keep GPU-first behavior and conversion API semantics stable.
- Separate operator/internal docs from public/product guidance.

### Acceptance Criteria

- [ ] Internal backend callers have a documented direct lane that does not
  require browser Gateway routing.
- [ ] Direct internal callers use the Sir Convert `InternalIdentityContextV1`
  authorization profile for job and artifact authorization.
- [ ] Local operator tunnel lane remains documented and tested.
- [ ] Operator credentials are explicit and never persisted in reports.
- [ ] GPU-backed conversion proof still works through the local lane.
- [ ] Docs no longer confuse direct local, internal, and public lanes.

### Test Requirements

- [ ] Internal network smoke proof.
- [ ] Local tunnel CLI proof.
- [ ] GPU/readiness proof through sanctioned wrappers.
- [ ] Docs validation.

### Done Definition

Done when internal and local operator workflows are preserved with durable
evidence and no public-access ambiguity.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
