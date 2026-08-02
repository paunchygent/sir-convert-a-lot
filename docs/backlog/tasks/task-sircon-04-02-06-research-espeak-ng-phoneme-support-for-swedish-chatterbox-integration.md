---
type: task
id: TASK-SIRCON-04-02-06
title: Research eSpeak NG phoneme support for Swedish Chatterbox integration
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-04-02
task_kind: story
acceptance_criteria:
- 'The research note is grounded in official upstream sources only: - `resemble-ai/chatterbox`
  - `espeak-ng/espeak-ng` - any proposed helper library''s official repo/docs'
- The task records whether the current Chatterbox API used by this repo can accept
  phoneme strings without undocumented internals.
- The task records that Swedish phoneme support must be benchmarked on Hemma rather
  than assumed from generic multilingual marketing copy.
- The task ends with a recommended task setup for the next slices rather than jumping
  directly to implementation.
retired_ids:
- task-88-research-espeak-ng-phoneme-support-for-swedish-chatterbox-integration
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

Research whether eSpeak NG should be incorporated into the Swedish Chatterbox
pipeline, and if so, identify the safest repo-aligned integration boundary and
benchmark discipline before any implementation work starts.

## PR Scope

- Research only; no production code integration in this task.
- Verify the official Chatterbox input surface that the current repo uses:
  - `text`
  - `language_id`
  - `audio_prompt_path`
  - `exaggeration`
  - `cfg_weight`
- Verify whether direct phoneme-string input is documented by the Chatterbox
  maintainers for the current multilingual API.
- Verify the official eSpeak NG capability surface relevant to this repo:
  - text-to-phoneme conversion
  - language coverage and Swedish verification steps
  - CLI/runtime packaging expectations
- Produce one reference note that compares possible integration boundaries:
  - offline preprocessing tool
  - benchmark-only sidecar/helper container
  - in-process runtime dependency
  - optional text-normalization experiment only
- End with a doc-first recommendation for the next implementation slice.

## Deliverables

- [ ] Reference note with official-source findings and incorporation options.
- [ ] Explicit statement of whether direct phoneme input is documented for the
  current Chatterbox multilingual API.
- [ ] Recommended docs-as-code follow-on task sequence for implementation, if
  the research outcome is positive.

## Acceptance Criteria

- [ ] The research note is grounded in official upstream sources only:
  - `resemble-ai/chatterbox`
  - `espeak-ng/espeak-ng`
  - any proposed helper library's official repo/docs
- [ ] The task records whether the current Chatterbox API used by this repo can
  accept phoneme strings without undocumented internals.
- [ ] The task records that Swedish phoneme support must be benchmarked on Hemma
  rather than assumed from generic multilingual marketing copy.
- [ ] The task ends with a recommended task setup for the next slices rather
  than jumping directly to implementation.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
