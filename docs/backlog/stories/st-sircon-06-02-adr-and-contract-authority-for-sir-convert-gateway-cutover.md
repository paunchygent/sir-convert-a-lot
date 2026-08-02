---
type: story
id: ST-SIRCON-06-02
title: ADR and contract authority for Sir Convert gateway cutover
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
- ADR-0009 is accepted or explicitly revised with unresolved questions tracked.
- The inventory reference contains enough caller/lane data to support migration sequencing.
- The Sir Convert `InternalIdentityContextV1` authorization profile is locked or the
  ADR remains proposed.
- Converter and downstream docs distinguish public Gateway, internal direct, and local
  operator lanes.
- The ADR names stop conditions for breaking existing internal and local offload use
  cases.
retired_ids:
- story-34-adr-and-contract-authority-for-sir-convert-gateway-cutover
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
Establish the normative decision and contract authority for moving Sir Convert-a-Lot public/product access behind HuleEdu Gateway while retaining internal service and local operator lanes.
## Scope
- Publish and review ADR-SIRCON-0008.
- Keep the caller/access-lane inventory reference as decision input.
- Treat Task 259 as a hard prerequisite for ADR acceptance so the Sir-specific
`InternalIdentityContextV1` authorization profile is not deferred.
- Update converter, downstream integration, internal adapter, and runbook
surfaces after the ADR is accepted.
- Record cross-repo HuleEdu/Skriptoteket implementation handoff boundaries.
## Acceptance Criteria
- [ ] ADR-SIRCON-0008 is accepted or explicitly revised with unresolved questions
tracked.
- [x] The inventory reference contains enough caller/lane data to support
migration sequencing.
- [x] The Sir Convert `InternalIdentityContextV1` authorization profile is
locked or the ADR remains proposed.
- [ ] Converter and downstream docs distinguish public Gateway, internal
direct, and local operator lanes.
- [ ] The ADR names stop conditions for breaking existing internal and local
offload use cases.
## Test Requirements
- [ ] `pdm run docs-validate`
- [ ] `pdm run handoff-validate`
- [ ] `git diff --check`
## Done Definition
Done when the ADR and migration reference are accepted as the governing authority for implementation tasks.
## Checklist
- [ ] ADR and docs authority complete
- [ ] Tests and validations complete
- [ ] Docs synchronized

