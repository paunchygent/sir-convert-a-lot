---
type: story
id: ST-SIRCON-06-01
title: Sir Convert gateway-fronted public access and internal lane migration
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
- HuleEdu and Skriptoteket consumer cutover decisions are recorded.
- Direct public conversion routes are removed, blocked, or deliberately reduced after
  consumers move.
- Browser-derived backend jobs do not collapse to global service-key ownership.
- Internal and local operator lanes remain usable.
- Public-edge and default-host behavior remain fail-closed.
- Pre-final testing keeps the direct public Sir Convert web surface disabled or fail-closed.
- Final live testing deliberately re-enables the intended public edge and proves only
  approved Gateway/internal/operator lanes work.
- Final proof covers all target lanes.
retired_ids:
- story-33-sir-convert-gateway-fronted-public-access-and-internal-lane-migration
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

## Historical Source Content

Implementation slice with acceptance-driven scope.

## Objective

Coordinate the migration from direct public Sir Convert access to the
Gateway-fronted product lane without breaking internal service consumers or
operator GPU-offload workflows.

## Scope

- Sequence consumer migration after inventory and ADR approval.
- Move browser/product callers to HuleEdu Gateway routes.
- Keep backend/internal workflows on a sanctioned internal lane where Gateway is
  not the right boundary.
- Require any user-originated backend-submitted workload to carry
  Gateway-issued `InternalIdentityContextV1` with audience `sir-convert-a-lot`
  through to Sir Convert.
- Restrict `convert.hule.education` only after proof that required consumers
  have a replacement lane.
- Keep direct public web access to Sir Convert disabled or fail-closed before
  the final live proof window.
- Re-enable the intended public edge as part of final live testing only after
  Gateway, internal, and operator replacement lanes are ready to prove.
- Preserve rollback and observability for the cutover window.

## Acceptance Criteria

- [ ] HuleEdu and Skriptoteket consumer cutover decisions are recorded.
- [ ] Direct public conversion routes are removed, blocked, or deliberately
  reduced after consumers move.
- [ ] Browser-derived backend jobs do not collapse to global service-key
  ownership.
- [ ] Internal and local operator lanes remain usable.
- [ ] Public-edge and default-host behavior remain fail-closed.
- [ ] Pre-final testing keeps the direct public Sir Convert web surface
  disabled or fail-closed.
- [ ] Final live testing deliberately re-enables the intended public edge and
  proves only approved Gateway/internal/operator lanes work.
- [ ] Final proof covers all target lanes.

## Test Requirements

- [ ] Public unauthenticated probes fail closed.
- [ ] Direct `convert.hule.education` web access is disabled or fail-closed
  before final live proof.
- [ ] Final live proof re-enables the intended public edge and verifies the
  ADR-0009 fail-closed/reserved posture for direct non-Gateway traffic.
- [ ] Gateway-authenticated conversion flow succeeds.
- [ ] Internal direct service-call proof succeeds.
- [ ] Local tunnel/offload proof succeeds.
- [ ] Unknown-host/default-host probe still returns reserved placeholder.

## Done Definition

Done when product traffic is Gateway-fronted, direct public exposure is
restricted, and the internal/operator lanes have durable proof.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
