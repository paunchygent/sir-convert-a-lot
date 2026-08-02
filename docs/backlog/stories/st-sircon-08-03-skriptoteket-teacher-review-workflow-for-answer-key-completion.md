---
type: story
id: ST-SIRCON-08-03
title: Skriptoteket teacher review workflow for answer-key completion
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
epic: EPIC-SIRCON-08
links:
  decisions: []
acceptance_criteria:
- Skriptoteket contract docs can be created from Sir Convert authority without duplicating
  parser/provider rules.
- The UI flow distinguishes source-bound answers, teacher/manual answers, LLM suggestions,
  applied reviewed answers, and unresolved manual follow-up.
- Teacher acceptance of a suggestion is represented as a manual overlay on a subsequent
  request, not retroactively as parser evidence.
- Missing-answer-key state remains an authoring blocker until a real answer-key correction
  is supplied; accepted-current-state export is not an overlay review decision or
  local UI flag in the active workflow.
- The UI consumes readiness classes such as `ready`, `needs_teacher_answer_key`, `unsupported_target_shape`,
  and `target_validation_failed` without collapsing them into one generic blocked
  state or reintroducing accepted-current-state export as authoring state.
- The durable teacher-correction API direction is source-neutral and producer-owned;
  the matching-specific transport is superseded and abandoned rather than treated
  as a route-per-item-type architecture, transitional route, or compatibility layer.
  PR-0332 may consume implemented non-matching unified corrections only after HuleEdu
  exposes the unified edge, and waits for Task 332 before matching correction consumption.
- Public Exam Converter jobs remain remote-provider-forbidden unless a signed public
  grant version explicitly opts in.
- HuleEdu LLM Provider reuse is treated as a future provider-surface task, not as
  a blocker for the first Sir Convert implementation.
retired_ids:
- story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion
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
Define the cross-product workflow that lets Skriptoteket teachers review, accept, or override answer-key completion while Sir Convert remains the conversion producer and HuleEdu remains an optional future provider/API owner.
## Scope
- Publish the Sir Convert contract details Skriptoteket needs for overlay
creation: source IR manifest item summaries, source item fingerprints, overlay schema, completion modes, manual follow-up report, completion report, target readiness report, `digiexam_migration_bundle_v2`, and named artifacts.
- Keep Skriptoteket as a consumer/UI owner: it may collect teacher edits,
submit overlays, show reports, and save final artifacts, but it must not infer answer keys outside the governed overlay/manual-key path.
- Define teacher-review states for source evidence, teacher overlay,
LLM-suggested answer keys, manual follow-up, and accepted/applied keys.
- Define that Skriptoteket submits review decisions and item edits back to Sir
Convert through producer-owned correction contracts. It must not treat local UI acceptance as file readiness and must refresh target readiness from Sir Convert before enabling PDF/QTI download or save.
- Define that accepted-current-state export is no longer part of teacher
authoring/correction state. Missing answer keys remain missing until the teacher supplies real answer-key corrections. Any future incomplete export must be a separate export-only request contract.
- Use Sir Convert's unified `manual_matching_answer_key` correction entry for
matching-capable source flows. Skriptoteket must not invent a local matching key shape, submit retired `left_id`/`right_id` aliases, or add matching to DigiExam overlays.
- Treat the Task 324 matching route as superseded and abandoned. It must not be
proxied, consumed, or preserved as an adapter, shim, alias, wrapper, temporary transitional route, or compatibility layer.
- ADR-SIRCON-0010 accepts the next Sir Convert producer direction as one
source-neutral correction/apply contract, expected at `POST /v2/exam-authoring/corrections/apply`, with typed entries for item text/stem/prompt correction, point correction, manual choice keys, manual gap/open-cloze accepted values, manual matching keys, review decisions, and candidate suppression.
- Task 327 published the Sir Convert contract artifact in
`docs/reference/ref-sircon-general-exam-authoring-corrections-apply-contract-exam-authoring-corrections-apply-contract.md`; Task 330 added the unified route/OpenAPI hard cut; Task 331 added signed producer source-state authority and DigiExam-backed text/point/choice/gap source-state surfaces.
- Task 333 completed the Sir Convert runtime continuation for non-matching
unified correction entries. HuleEdu/Skriptoteket may proceed with the implemented non-matching families only after HuleEdu exposes the unified authenticated edge: point, manual choice, manual gap/open-cloze, and item text corrections against producer-issued DigiExam state.
- Task 337 removes accepted-current-state export from authoring correction
contracts. Downstream durable sessions must not persist or replay `review_decision` / `accept_current_state_for_export` as correction state.
- Task 373 completed the compact review-state projection follow-up. Sir Convert
is the producer of item-level answer-key review semantics so Skriptoteket can render compact states without re-deriving truth from multiple artifact families.
- Story 57 is the cross-repo tracking surface for Task 373 and Skriptoteket
PR-0406. It owns the final live production browser proof gate with the tracked DXE fixture before this workflow can be called end-to-end complete.
- Task 332 remains the separate matching-capable producer task. Skriptoteket
must not submit `manual_matching_answer_key` until Task 332 emits real matching source state and proves unified-route apply behavior.
- Skriptoteket must not build new teacher-correction surfaces around the
abandoned adapter/route-per-item pattern. After the Sir Convert runtime hard cut and a governed consumer implementation slice, new consumer work should target the unified correction/apply contract.
- Keep HuleEdu as the authenticated edge proxy for that one contract and
Skriptoteket as its teacher-correction consumer. Do not add more item-specific HuleEdu Gateway routes unless a future governed task proves why the unified contract cannot cover the case.
- Preserve public/authenticated access boundaries from the existing Exam
Converter grant lane; remote LLM fallback for public jobs requires a future signed grant contract.
- Record the HuleEdu LLM Provider decision checkpoint: use Sir Convert's
service-backed provider harness first, then evaluate a new HuleEdu generic structured-completion API only after the local-first contract exists.
## Acceptance Criteria
- [ ] Skriptoteket contract docs can be created from Sir Convert authority
without duplicating parser/provider rules.
- [ ] The UI flow distinguishes source-bound answers, teacher/manual answers,
LLM suggestions, applied reviewed answers, and unresolved manual follow-up.
- [ ] Teacher acceptance of a suggestion is represented as a manual overlay on
a subsequent request, not retroactively as parser evidence.
- [ ] Missing-answer-key state remains an authoring blocker until a real
answer-key correction is supplied; accepted-current-state export is not an overlay review decision or local UI flag in the active workflow.
- [ ] The UI consumes readiness classes such as `ready`,
`needs_teacher_answer_key`, `unsupported_target_shape`, and `target_validation_failed` without collapsing them into one generic blocked state or reintroducing accepted-current-state export as authoring state.
- [ ] The durable teacher-correction API direction is source-neutral and
producer-owned; the matching-specific transport is superseded and abandoned rather than treated as a route-per-item-type architecture, transitional route, or compatibility layer. PR-0332 may consume implemented non-matching unified corrections only after HuleEdu exposes the unified edge, and waits for Task 332 before matching correction consumption.
- [ ] Public Exam Converter jobs remain remote-provider-forbidden unless a
signed public grant version explicitly opts in.
- [ ] HuleEdu LLM Provider reuse is treated as a future provider-surface task,
not as a blocker for the first Sir Convert implementation.
## Test Requirements
- [ ] Skriptoteket adapter tests must prove overlay source binding is sent
exactly as supplied by Sir Convert manifest data.
- [ ] Consumer tests must prove the UI cannot submit raw `.dxe`, result PDF
text, student data, or raw artifacts inside overlay context.
- [ ] Cross-repo proof must include authenticated and public/grant routes where
applicable, with explicit remote-provider policy evidence.
- [ ] If HuleEdu LLM Provider is extended later, conformance tests must prove it
returns schema-specific structured JSON or typed failure without comparison-only result fields.
## Done Definition
This story is done when the Sir Convert-owned contract is sufficient for Skriptoteket to build a teacher review workflow and for HuleEdu to make an informed provider-API decision without duplicating conversion policy.
## Checklist
- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized

