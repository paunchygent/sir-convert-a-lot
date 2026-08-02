---
type: task
id: TASK-SIRCON-01-05-02
title: Container operations runbook and Hemma deployment verification for dockerized
  service
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
story: ST-SIRCON-01-05
task_kind: story
acceptance_criteria:
- '- [ ] Operator can follow runbook only and reach healthy ready services on Hemma.'
- '- [ ] Verification catches stale revision or profile/data-root mismatch deterministically.'
- '- [ ] GPU-first invariant remains enforced under containerized startup/restart
  flow.'
- '- [ ] Manual smoke conversion via tunnel is documented and evidenced.'
retired_ids:
- task-24-container-operations-runbook-and-hemma-deployment-verification-for-dockerized-service
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

Publish and validate canonical container operations flow on Hemma (deploy, verify, restart,
recover) so operators can run the dockerized service safely with GPU-first guarantees.

## PR Scope

- Update runbook with canonical container lifecycle commands (deploy/update/rollback/restart).
- Codify verification flow that combines health, readiness, and GPU runtime checks.
- Add/extend script-backed checks for Hemma deployment correctness where needed.
- Validate end-to-end command flow against real Hemma topology and tunnel-first local checks.

Out of scope:

- service image/compose implementation internals (Task 22),
- core persistence behavior implementation (Task 23).

## Deliverables

- [ ] Runbook section for dockerized service operations on Hemma.
- [ ] Canonical command set for deploy/pull/restart/verify with no ad hoc shell transport.
- [ ] Verification evidence for readiness + GPU runtime + conversion smoke path.
- [ ] Backlog/context docs updated with final operational contract.

## Acceptance Criteria

- [ ] Operator can follow runbook only and reach healthy ready services on Hemma.
- [ ] Verification catches stale revision or profile/data-root mismatch deterministically.
- [ ] GPU-first invariant remains enforced under containerized startup/restart flow.
- [ ] Manual smoke conversion via tunnel is documented and evidenced.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
