---
type: task
id: TASK-SIRCON-05-05-01
title: Launch the first clean base restart after the bounded stability gate
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
story: ST-SIRCON-05-05
task_kind: story
acceptance_criteria:
- "[ ] The task does not start before Story 31 records an explicit fresh-start\n \
  \ stabilization proof in the training reference ledger that justifies a larger\n\
  \  clean-start proof lane."
- "[ ] The first restart acceptance gate is completion of the first scheduled\n  eval\
  \ at step `100` without a non-finite guard event."
- "[ ] Any new restart failure window is written back into the training\n  reference\
  \ ledger immediately rather than treated as an informal note."
retired_ids:
- task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate
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
Launch the first clean base restart only after the repo records a truthful fresh-start stabilization proof that shows stable bundle learning is back on the canonical clean-semantics lane.
## PR Scope
- Treat Story 29 and Story 30 as closed prerequisite evidence:
  - replay-family rescue is exhausted
  - clean text semantics are now a correctness baseline, not a stability proof
  - fresh-start Candidate 1 also failed before stable learning was recovered
- Block this task until Story 31 records:
  - one bounded talker-core stabilization surface (`T216`)
  - one passing local finiteness gate (`T215`)
  - one positive fresh-start governed Hemma proof (`T217`) that justifies a
larger clean-start proof lane
- Launch from `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, not from a legacy checkpoint.
- Use the winning mitigation contract from the proof phase.
- If the winning mitigation confirms `text_span_only` as the right fix, remove
`legacy_codec_span` from the live restart lane before launch.
- Use the canonical scheduled posture:
  - checkpoint every `500`
  - eval every `100`
  - retain newest `3`
- Record the restart result immediately in the training reference ledger.
## Deliverables
- [ ] One proof-gated clean restart launch record exists.
- [ ] One operator-facing ledger entry records which proof gate justified the
restart.
- [ ] If the proof closed in favor of `text_span_only`, one explicit cleanup
record exists showing `legacy_codec_span` was removed before restart.
- [ ] One restart acceptance record states whether step `100` eval completed
without a non-finite guard event.
## Acceptance Criteria
- [ ] The task does not start before Story 31 records an explicit fresh-start
stabilization proof in the training reference ledger that justifies a larger clean-start proof lane.
- [ ] The first restart acceptance gate is completion of the first scheduled
eval at step `100` without a non-finite guard event.
- [ ] Any new restart failure window is written back into the training
reference ledger immediately rather than treated as an informal note.
## Checklist
- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

