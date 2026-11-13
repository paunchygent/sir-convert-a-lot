---
type: task
id: TASK-SIRCON-05-03-03
title: Persist precomputed Qwen reference mels in the pilot bundle and training manifest
  contract
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
story: ST-SIRCON-05-03
task_kind: story
acceptance_criteria:
- '[ ] The task lands only if `T161` documented that cache-only is insufficient.'
- "[ ] The deterministic pilot-bundle contract remains reviewable and\n  relocation-safe\
  \ after the new artifact family is added."
- "[ ] A bounded Hemma comparison shows that precomputed bundle-level mels\n  materially\
  \ improve throughput over runtime-only mel extraction."
retired_ids:
- task-164-persist-precomputed-task-101-qwen-reference-mels-in-the-pilot-bundle-and-training-manifest-contract
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

### Context

State the bounded implementation or proof need and the parent story behavior it
supports.

### Decision And Assumption Ledger

Every material implementation choice must already be closed by an accepted
source before scaffolding this task.

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

### Story Contract Slice

Define the single-responsibility implementation or proof slice derived from the
parent story. Name the exact surfaces this task may change.

### Contract Inputs

- Accepted ADRs, references, runbooks, reviews, or prior backlog contracts that
  constrain this task.

### Plan

State the smallest implementation approach that satisfies the story slice and
acceptance criteria.

### Implementation Steps

List ordered steps small enough to execute and verify without inventing scope.

### Proof

- Selected proof mode and applicability basis.
- Focused pre-change command and expected result when required.
- The same focused post-change command and expected result.

### Validation

List the exact focused and repository gates required before closeout and retain
concise results after they run.

### Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to planning.

### Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

### Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

### Plan Document Review

Record findings, evidence, permitted next step, and residual risk. The
`readiness_review` frontmatter mapping is the machine authority for gate status.

### Implementation Review

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

PR-sized execution unit; may be linked to a story or standalone.
### Objective
Expand the Task 101 pilot-bundle contract to include precomputed reference mels only if the earlier cache-and-dataloader tasks still fail to meet the story’s saturation target.
### Why This Exists
`T161` is the intentionally lower-risk first attempt to eliminate duplicate `ref_mel` work. If cache-only optimization still leaves the steady-state GPU busy below the story gate, the next coherent move is to precompute and persist the reference mels in the deterministic pilot bundle rather than recomputing them at runtime forever.
### PR Scope
- Extend the deterministic Task 101 pilot-bundle materialization path to write
precomputed reference-mel artifacts for the stable canonical speaker refs.
- Extend the prepared-manifest or related training-row contract so the trainer
can load precomputed mels when present.
- Keep legacy bundle compatibility explicit:
  - either via fallback runtime mel extraction,
  - or via a fail-closed contract bump that is clearly documented.
- Measure the storage impact and bundle-build cost of the new artifact family.
### Non-Goals
- Do not open this task before `T161` explicitly concludes that cache-only is
insufficient.
- Do not broaden the bundle contract to unrelated feature tensors here.
### Deliverables
- [ ] Precomputed reference-mel artifact contract defined.
- [ ] Task 101 bundle builder writes the new artifacts.
- [ ] Task 101 trainer consumes precomputed mels when available.
- [ ] Storage-cost and throughput evidence are documented.
### Acceptance Criteria
- [ ] The task lands only if `T161` documented that cache-only is insufficient.
- [ ] The deterministic pilot-bundle contract remains reviewable and
relocation-safe after the new artifact family is added.
- [ ] A bounded Hemma comparison shows that precomputed bundle-level mels
materially improve throughput over runtime-only mel extraction.
### Validation
- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma evidence records bundle-size cost and runtime gain.
### Checklist
- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
