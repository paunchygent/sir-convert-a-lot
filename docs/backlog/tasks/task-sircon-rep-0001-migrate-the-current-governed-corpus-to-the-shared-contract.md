---
type: task
id: TASK-SIRCON-REP-0001
title: Migrate the current governed corpus to the shared contract
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
task_kind: repository
acceptance_criteria:
- Sir Convert-a-Lot's current governed corpus conforms to the shared contract while
  terminal records remain historical and historical-validator execution remains disabled.
---

## Context

State the repository problem, current behavior, and why this bounded task is
needed.

## Impact And Escalation

State the affected repository-governance or developer-tooling surface. Escalate
product behavior into an epic and story instead of implementing it here.
Product behavior excludes skill prose, repository-governance prose including
`AGENTS.md`, optimization, bug fixing, and behavior-neutral implementation
details that affect neither producers nor consumers.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

## Plan

State the smallest implementation approach that satisfies the accepted ledger
and acceptance criteria.

## Implementation Steps

List ordered, bounded edits and their integration order. Do not add work that is
not derived from the task contract.

## Proof

- Selected proof mode and applicability basis.
- Focused pre-change command and expected result when required.
- The same focused post-change command and expected result.

## Validation

List the exact repository commands required before closeout and retain concise
results after they run.

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to the task owner.

## Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

## Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

## Readiness

Record ledger closure, authority evidence, permitted next step, and residual
risk. The `readiness_review` frontmatter mapping is the machine authority for
gate status.

## Closeout

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.
