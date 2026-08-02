---
type: task
id: TASK-SIRCON-06-01-01
title: Restrict convert.hule.education public edge after gateway cutover
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
story: ST-SIRCON-06-01
task_kind: story
acceptance_criteria:
- '- [ ] Public anonymous traffic cannot create, read, or download jobs/artifacts.'
- '- [ ] `convert.hule.education` returns the ADR-0009 fail-closed/reserved posture.
  Any status page or external M2M API is blocked unless a separate accepted ADR exists.'
- '- [ ] Product/browser access continues through Gateway.'
- '- [ ] Internal and local operator lanes are unaffected.'
- '- [ ] Linked HuleEdu/Skriptoteket route implementation and consumer migration signoffs
  exist before this task changes the public host.'
retired_ids:
- task-262-restrict-convert-hule-education-public-edge-after-gateway-cutover
---

## Context

State the bounded implementation or proof need and the parent story behavior it
supports.

## Decision And Assumption Ledger

Every material implementation choice must already be closed by an accepted
source before scaffolding this task.

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

## Story Contract Slice

Define the single-responsibility implementation or proof slice derived from the
parent story. Name the exact surfaces this task may change.

## Contract Inputs

- Accepted ADRs, references, runbooks, reviews, or prior backlog contracts that
  constrain this task.

## Plan

State the smallest implementation approach that satisfies the story slice and
acceptance criteria.

## Implementation Steps

List ordered steps small enough to execute and verify without inventing scope.

## Proof

- Selected proof mode and applicability basis.
- Focused pre-change command and expected result when required.
- The same focused post-change command and expected result.

## Validation

List the exact focused and repository gates required before closeout and retain
concise results after they run.

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to planning.

## Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

## Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

## Plan Document Review

Record findings, evidence, permitted next step, and residual risk. The
`readiness_review` frontmatter mapping is the machine authority for gate status.

## Implementation Review

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Restrict the direct `convert.hule.education` public edge to the fail-closed
reserved/default posture after Gateway and internal/operator replacement lanes
are proven.

## PR Scope

- Enforce the ADR-0009 public-host posture: reserved fail-closed/default
  response.
- Remove or block direct public job APIs.
- Remove public docs/OpenAPI/metrics/detailed readiness exposure.
- Keep nginx-proxy default-host behavior fail-closed.
- Capture public-edge proof artifacts.

## Deliverables

- [ ] Updated compose/proxy/public-edge configuration.
- [ ] Public deny proof for job APIs and metadata endpoints.
- [ ] Unknown-host/default-host proof.
- [ ] Runbook update.

## Acceptance Criteria

- [ ] Public anonymous traffic cannot create, read, or download jobs/artifacts.
- [ ] `convert.hule.education` returns the ADR-0009 fail-closed/reserved
  posture. Any status page or external M2M API is blocked unless a separate
  accepted ADR exists.
- [ ] Product/browser access continues through Gateway.
- [ ] Internal and local operator lanes are unaffected.
- [ ] Linked HuleEdu/Skriptoteket route implementation and consumer migration
  signoffs exist before this task changes the public host.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
