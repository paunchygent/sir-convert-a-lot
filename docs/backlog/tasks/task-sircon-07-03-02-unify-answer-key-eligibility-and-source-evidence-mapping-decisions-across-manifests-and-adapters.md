---
type: task
id: TASK-SIRCON-07-03-02
title: Unify answer-key eligibility and source-evidence mapping decisions across manifests
  and adapters
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
story: ST-SIRCON-07-03
task_kind: story
acceptance_criteria:
- Choice, multiple-response, and gap-fill eligibility are classified in one domain
  service or policy object rather than duplicated in manifest code.
- Task 309 output-mode counts still distinguish vLLM choice from JSON Schema exactly
  as the governed planner policy requires.
- Text-only validation/advisory policy keeps embedded-asset rows skipped as `unsupported_assets`;
  Qwen3.6 vision-capable policy can include supported PNG/JPEG embedded assets without
  changing source provenance.
- Adding a new source-evidence family requires changing one mapper, not multiple string-check
  helpers.
- LLM completion lineage remains candidate metadata and never becomes parser/source
  provenance.
- No raw prompt, provider response, item text, alternative text, or gap text is introduced
  into retained artifacts.
retired_ids:
- task-317-unify-answer-key-eligibility-and-source-evidence-mapping-decisions-across-manifests-and-adapters
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

Unify duplicated answer-key eligibility/output-mode classification and typed
source-evidence provenance mapping so manifests and adapters consume explicit
domain decision surfaces instead of repeating string and item-type checks.

This task follows Task 312 without reopening Task 312. The provider planner now
owns per-item provider request shape; the remaining drift risk is that Task 309
manifest planning and source-evidence adapters can classify the same domain
state through separate branch logic.

## PR Scope

- Expose one answer-key candidate eligibility/output-mode classifier consumed
  by both live execution planning and the Task 309 validation manifest.
- Preserve Task 309 manifest fields and counts while deriving them from the
  shared decision surface.
- Include embedded-asset/vision eligibility as a policy input so text-only
  providers retain the 42-item default corpus while Qwen3.6 vision-capable
  runs can explicitly allow the 44 scored items proven by Task 309.
- Introduce a typed source-evidence family/provenance mapper for DigiExam DXE,
  graded-result PDF correct labels, teacher overlay, and reviewed completion
  evidence.
- Replace scattered source-family string-to-provenance mapping checks in gap
  contracts and DigiExam authoring adapters with the mapper.
- Do not change parser provenance semantics, advisory report privacy,
  effective IR application, or renderer output.

## Deliverables

- [ ] Shared answer-key candidate eligibility/output-mode classifier.
- [ ] Task 309 manifest generation wired to the shared classifier.
- [ ] Shared embedded-asset/vision eligibility policy preserving separate
  text-only and vision-capable outcomes.
- [ ] Typed source-evidence family/provenance mapper.
- [ ] Adapter and gap-contract tests proving existing classifications are
  unchanged.

## Acceptance Criteria

- [ ] Choice, multiple-response, and gap-fill eligibility are classified in
  one domain service or policy object rather than duplicated in manifest code.
- [ ] Task 309 output-mode counts still distinguish vLLM choice from JSON
  Schema exactly as the governed planner policy requires.
- [ ] Text-only validation/advisory policy keeps embedded-asset rows skipped as
  `unsupported_assets`; Qwen3.6 vision-capable policy can include supported
  PNG/JPEG embedded assets without changing source provenance.
- [ ] Adding a new source-evidence family requires changing one mapper, not
  multiple string-check helpers.
- [ ] LLM completion lineage remains candidate metadata and never becomes
  parser/source provenance.
- [ ] No raw prompt, provider response, item text, alternative text, or gap text
  is introduced into retained artifacts.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
