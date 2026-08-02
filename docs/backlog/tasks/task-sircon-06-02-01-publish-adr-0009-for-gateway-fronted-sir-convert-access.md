---
type: task
id: TASK-SIRCON-06-02-01
title: Publish ADR-0009 for Gateway-fronted Sir Convert access
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
story: ST-SIRCON-06-02
task_kind: story
acceptance_criteria:
- '- [ ] ADR explicitly preserves internal service direct access.'
- '- [ ] ADR explicitly preserves local operator GPU-offload access.'
- '- [ ] ADR explicitly rejects anonymous/direct public job API access as the normal
  product lane.'
- '- [ ] ADR names HuleEdu `InternalIdentityContextV1` with audience `sir-convert-a-lot`
  as the first enforced identity model for Gateway/user-originated traffic.'
- '- [ ] ADR keeps direct public host posture fail-closed/reserved unless a separate
  accepted ADR creates another public surface.'
- '- [ ] Docs validation passes.'
retired_ids:
- task-257-publish-adr-0009-for-gateway-fronted-sir-convert-access
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Finalize ADR-0009 as the accepted architecture decision for Gateway-fronted
public Sir Convert access and preserved internal/operator lanes.

### PR Scope

- Review and update the proposed ADR text after Task 256 inventory evidence.
- Keep ADR-0009 proposed until Task 259 locks Sir Convert's
  `InternalIdentityContextV1` authorization profile and the context-derived
  job/artifact authorization model.
- Record accepted access-lane matrix and migration stop conditions.
- Link ADR-0009 from converter docs, downstream integration docs, runbook, and
  active backlog items.
- Keep the ADR explicit about what moves to Gateway and what stays direct
  internal/operator.

### Deliverables

- [ ] Accepted ADR-0009.
- [x] Completed Task 259 identity-contract prerequisite.
- [ ] Updated links from affected docs.
- [ ] Follow-up implementation tasks are confirmed or revised.

### Acceptance Criteria

- [ ] ADR explicitly preserves internal service direct access.
- [ ] ADR explicitly preserves local operator GPU-offload access.
- [ ] ADR explicitly rejects anonymous/direct public job API access as the
  normal product lane.
- [ ] ADR names HuleEdu `InternalIdentityContextV1` with audience
  `sir-convert-a-lot` as the first enforced identity model for
  Gateway/user-originated traffic.
- [ ] ADR keeps direct public host posture fail-closed/reserved unless a
  separate accepted ADR creates another public surface.
- [ ] Docs validation passes.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
