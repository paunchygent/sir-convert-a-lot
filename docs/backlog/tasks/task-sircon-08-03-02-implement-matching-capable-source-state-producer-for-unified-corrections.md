---
type: task
id: TASK-SIRCON-08-03-02
title: Implement matching-capable source-state producer for unified corrections
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
story: ST-SIRCON-08-03
task_kind: story
acceptance_criteria:
- 'A real producer-owned source state contains at least one item with `item_type:
  matching` and a non-empty `matching_interactions` collection.'
- The matching interaction exposes stable `interaction_id`, source choice IDs, target
  choice IDs, association bounds, current answer-key provenance, source evidence,
  and source-item fingerprint binding.
- The source-state issuer returns the signed bundle for that producer using only server-owned
  producer state.
- A focused runtime test submits `manual_matching_answer_key` with issued source IDs
  and target IDs, receives an accepted entry, and gets target readiness/artifact availability
  according to the unified contract.
- A negative regression proves DigiExam producer-issued state with zero matching interactions
  cannot be used as matching authority.
- OpenAPI continues to expose only the unified correction routes and omits the abandoned
  Task 324 route.
retired_ids:
- task-332-implement-matching-capable-source-state-producer-for-unified-corrections
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

Governed follow-up for enabling real downstream use of
`manual_matching_answer_key` on the unified correction route.

## Objective

Wire a genuinely matching-capable producer into the signed correction
source-state issuance path so downstream consumers can submit
`manual_matching_answer_key` against producer-owned matching interaction IDs,
source IDs, target IDs, bounds, and current answer-key provenance.

This task exists because DigiExam `.dxe` runtime state does not contain
canonical matching item structure. Task 331 must not fabricate matching
interactions from DigiExam `unknown` items, prompt text, answer prose, or
browser-local draft state.

## PR Scope

- Resolve or implement a source producer that emits real
  `ExamAuthoringMatchingInteraction` state from source evidence that actually
  contains matching structure.
- Persist signed correction source-state sidecars for that producer through the
  normal producer runtime path, not through test-only fixture seeding.
- Ensure `/v2/exam-authoring/corrections/source-state/issue` can issue the
  matching source state with Sir Convert-owned authority.
- Prove `/v2/exam-authoring/corrections/apply` accepts a
  `manual_matching_answer_key` entry using only the issued source state and
  binding.
- Keep the abandoned Task 324 route absent. Do not add an adapter, shim, alias,
  wrapper, compatibility route, or route-preserving frontend contract.

## Deliverables

- [ ] Matching-capable producer selected or implemented with real source
  evidence.
- [ ] Normal runtime source-state sidecar emission for matching items.
- [ ] Source-state issuer proof for the matching-capable producer.
- [ ] Unified correction apply proof for `manual_matching_answer_key` using the
  issued bundle.
- [ ] Negative proof that DigiExam non-matching state cannot authorize matching
  corrections.
- [ ] Contract docs, review state, OpenAPI snapshot, and handoff updated.

## Out of Scope

- DigiExam `.dxe` matching synthesis. DigiExam remains a non-matching source
  unless a later governed source-evidence task proves otherwise.
- Implementing choice, gap/open-cloze, point, text-patch, review-decision, or
  candidate-suppression runtime application. The DigiExam-backed non-matching
  runtime continuation belongs to Task 333 before HuleEdu/Skriptoteket consume
  those entries through the unified product edge.

## Acceptance Criteria

- [ ] A real producer-owned source state contains at least one item with
  `item_type: matching` and a non-empty `matching_interactions` collection.
- [ ] The matching interaction exposes stable `interaction_id`, source choice
  IDs, target choice IDs, association bounds, current answer-key provenance,
  source evidence, and source-item fingerprint binding.
- [ ] The source-state issuer returns the signed bundle for that producer using
  only server-owned producer state.
- [ ] A focused runtime test submits `manual_matching_answer_key` with issued
  source IDs and target IDs, receives an accepted entry, and gets target
  readiness/artifact availability according to the unified contract.
- [ ] A negative regression proves DigiExam producer-issued state with zero
  matching interactions cannot be used as matching authority.
- [ ] OpenAPI continues to expose only the unified correction routes and omits
  the abandoned Task 324 route.

## Validation Plan

- `pdm run openapi-export-v2`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- Focused matching-capable producer/issuer/apply tests.
- Focused OpenAPI route contract tests.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
