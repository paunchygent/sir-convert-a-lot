---
type: task
id: TASK-SIRCON-05-04-04
title: Align Dockerfiles Runbooks and Backlog to Domain-Centric Structure
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
story: ST-SIRCON-05-04
task_kind: story
acceptance_criteria:
- "[ ] `docker buildx build --load` for the Qwen image succeeds with the new\n  structure."
- '[ ] Runbook steps are verified against the new command names.'
- '[ ] `pdm run validate-docs` and `pdm run validate-tasks` pass.'
retired_ids:
- task-170-align-dockerfiles-runbooks-and-backlog-to-domain-centric-structure
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

Complete the domain-centric transition by updating all external references to the
ML pipeline, including Docker entrypoints, runbooks, and active backlog documentation.

## PR Scope

- Update `containers/qwen-finetune-hemma/Dockerfile` with the new in-container paths.
- Update `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
- Update `AGENTS.md` and related system-level docs.
- Move and update `tests/sir_convert_a_lot/task103_*.py` to `tests/sir_convert_a_lot/ml/qwen/preprocessing/`.
- Final audit of all `taskXXX` prefixes in the codebase.

## Deliverables

- [ ] Dockerfiles updated.
- [ ] Runbooks and AGENTS.md updated.
- [ ] Test suite aligned with the new structure.

## Acceptance Criteria

- [ ] `docker buildx build --load` for the Qwen image succeeds with the new
  structure.
- [ ] Runbook steps are verified against the new command names.
- [ ] `pdm run validate-docs` and `pdm run validate-tasks` pass.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
