---
type: task
id: TASK-SIRCON-06-01-02
title: Run Sir Convert gateway cutover proof and security review
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
- '- [ ] Public deny, Gateway allow, internal allow, and operator allow are all proven.'
- '- [ ] Final live proof includes deliberate re-enable of the intended public edge,
  not an accidental always-on direct public Sir Convert surface.'
- '- [ ] Proof commands and artifacts are reproducible, not narrative-only.'
- '- [ ] No high-severity review finding remains unresolved.'
- '- [ ] Rollback path is documented.'
retired_ids:
- task-263-run-sir-convert-gateway-cutover-proof-and-security-review
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

## Source Body Preservation

PR-sized execution unit; may be linked to a story or standalone.
## Objective
Run the final cutover verification and security review before declaring the Gateway-fronted Sir Convert access model complete.
## PR Scope
- Verify public anonymous deny behavior.
- Verify that direct public web access to Sir Convert is disabled or
fail-closed before the final live proof window.
- Re-enable the intended public edge during final live testing and prove that
only the approved Gateway/internal/operator lanes work.
- Verify Gateway-authenticated product flow.
- Verify direct internal service call flow.
- Verify local operator tunnel/offload flow.
- Verify docs/OpenAPI/metrics/readiness public exposure posture.
- Verify unknown-host/default-host fail-closed behavior.
- Capture durable report artifacts.
- Write proof artifacts under
`build/verification/gateway-cutover-sir-convert/`.
- Tie public-edge checks to the existing `hemma-deploy-and-verify` proof
contract where possible.
## Deliverables
- [ ] Public/internal/operator proof report.
- [ ] Pre-final public-web isolation proof showing direct
`convert.hule.education` access is disabled or fail-closed before final live proof.
- [ ] Final public-edge re-enable proof showing the intended Gateway-backed
public path works while direct non-Gateway traffic remains fail-closed.
- [ ] Security review findings or explicit no-finding record.
- [ ] Final cutover report artifacts.
- [ ] Canonical `report.md` and `report.json` under
`build/verification/gateway-cutover-sir-convert/`.
- [ ] Handoff/current docs update.
## Acceptance Criteria
- [ ] Public deny, Gateway allow, internal allow, and operator allow are all
proven.
- [ ] Final live proof includes deliberate re-enable of the intended public
edge, not an accidental always-on direct public Sir Convert surface.
- [ ] Proof commands and artifacts are reproducible, not narrative-only.
- [ ] No high-severity review finding remains unresolved.
- [ ] Rollback path is documented.
## Checklist
- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

