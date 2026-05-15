---
id: task-306-apply-reviewed-answer-key-completion-into-effective-ir
title: Apply reviewed answer-key completion into effective IR
type: task
status: completed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
labels:
  - effective-ir
  - answer-key-completion
  - reviewed-application
  - review-gate
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Apply reviewed and validated answer-key completion into the effective IR only
after the structured provider/advisory path exists and after matching plus
gapped/open-cloze answer-key shapes are first-class intermediary contracts.

This task owns reviewed application. It does not define matching pair fields or
gap accepted-value fields; Tasks 298 and 305 own those contract shapes.

## Planning Decisions

- Task 306 is an overlay-driven reviewed-application slice, not a new LLM
  execution slice.
- Task 297 remains candidate production only. Its
  `answer_key_completion_report_v1` output is advisory candidate lineage, not
  answer-key provenance.
- `local_llm_apply_missing_machine_marked_with_review` MUST NOT call a
  structured provider. It applies only teacher-reviewed completion data
  submitted with the request and fails closed when reviewed application data is
  absent, malformed, unbound, or semantically invalid.
- Sir Convert does not perform cross-job lookup for prior completion reports in
  this slice. Candidate digest, completion-report digest, candidate ID, schema
  version, prompt-template version, provider profile, and review decision ID are
  bounded lineage metadata. They are revalidated as submitted metadata, not as
  source evidence.
- Reviewed application is effective-only. It must not add LLM states to the
  parser/source `DigiExamAnswerKeyProvenance` enum or mutate the source IR.
- DigiExam `.dxe` still does not produce matching items. This task must not add
  a DigiExam matching bridge. Matching reviewed application remains governed by
  Task 298 for future matching-capable source adapters and source-neutral
  `ExamAuthoringIR v1` consumers.

## PR Scope

- Add effective answer-key provenance separate from source parser provenance.
- Add bounded answer-key lineage metadata separate from answer-key provenance
  and parser provenance. Lineage may point to an LLM completion report,
  provider profile, candidate digest, review decision, and whether the teacher
  accepted unchanged or edited before applying.
- Treat candidate digests as digests of canonical backend-validated candidate
  payloads from Task 297, not as hashes of raw provider responses, prompts, or
  provider-specific pre-validation output.
- Apply validated completion only in
  `local_llm_apply_missing_machine_marked_with_review` mode.
- Add a source-bound reviewed-completion overlay field, named
  `reviewed_completion_answer_key`, separate from `manual_answer_key`.
- Require report/review semantics that distinguish LLM-inferred output from
  teacher/manual overlay.
- Preserve source-bound evidence precedence over LLM completion.
- Consume the choice and gapped/open-cloze structured answer-key contracts
  without widening their shape.
- Keep malformed or semantically invalid output as manual follow-up, with no
  repair.
- Prove teacher-accepted suggestions can be resubmitted as manual overlay, but
  are not retroactively model provenance.
- Preserve matching semantics as a contract boundary only: whole-key reviewed
  or teacher-provided matching pair sets are valid under Task 298 for future
  matching-capable sources, but the DigiExam runtime does not apply matching in
  this task.
- Keep the `mixed` prohibition scoped to matching. Gapped/open-cloze can derive
  aggregate `mixed` later from per-accepted-value provenance under the Task 305
  contract.

## Reviewed Completion Shape

Add an overlay entry field shaped as:

- `reviewed_completion_answer_key.kind`: `choice` or `gap_fill`.
- `review_decision_id`: stable teacher review decision ID.
- `review_outcome`: `accepted_unchanged` or `teacher_edited`.
- `candidate_lineage`: bounded metadata containing completion-report digest,
  candidate ID, candidate payload digest, provider profile ID, schema name,
  schema version, prompt-template version, and backend validation state.
- `answer_payload`: the final reviewed answer payload. For accepted-unchanged
  candidates this payload must digest to the submitted candidate payload digest.
  For teacher-edited candidates it may differ, but must still validate against
  the same item-local ID/value rules.

Effective provenance mapping:

- `accepted_unchanged` -> effective answer-key provenance `reviewed` with LLM
  candidate lineage.
- `teacher_edited` -> effective answer-key provenance `teacher_provided` with
  candidate lineage showing the LLM candidate as the starting point.
- `manual_answer_key` without completion lineage remains
  `teacher_provided` with no LLM lineage.

Application order:

1. Parse source `.dxe` and write immutable source IR.
1. Apply source-bound teacher overlay item-content/manual-answer-key fields.
1. Apply source-bound reviewed completion entries only when
   `completion_mode=local_llm_apply_missing_machine_marked_with_review`.
1. Write `digiexam_effective_exam_v2` when renderer input changes.
1. Render Exam.net PDF/QTI and readiness reports from the effective exam.

The apply mode may emit an `answer_key_completion_report` artifact only as
bounded application/reporting evidence. It must not run the provider or recreate
raw advisory prompts/responses.

## Deliverables

- [x] Effective answer-key provenance model for reviewed completion.
- [x] Answer-key lineage metadata model for LLM candidate acceptance and
  teacher edits.
- [x] `reviewed_completion_answer_key` overlay contract with `extra=forbid`.
- [x] Apply mode for reviewed completion.
- [x] Applied completion service.
- [x] Completion report and effective IR update semantics.
- [x] Renderer/QTI tests proving applied effective keys are consumed only after
  validation and review.

## Acceptance Criteria

- [x] Source IR and parser provenance remain unchanged after applied
  completion.
- [x] Effective IR and bundle manifest identify LLM-inferred answer keys
  explicitly.
- [x] LLM completion metadata remains bounded lineage metadata. It must not be
  stored as parser/source provenance, raw prompt text, raw model response, or
  aggregate `mixed` matching provenance.
- [x] Apply mode performs no structured provider calls.
- [x] Apply mode without reviewed-completion overlay data fails closed and does
  not mutate renderer input.
- [x] Submitted candidate lineage is sufficient for review audit but is not
  treated as source evidence; no cross-job lookup is required.
- [x] Teacher-accepted suggestions can be resubmitted as manual overlay, but
  are not retroactively model provenance.
- [x] DigiExam runtime does not add matching application or a
  `DigiExamIntermediateExam -> ExamAuthoringIR matching` bridge.
- [x] Gapped/open-cloze application uses only the Task 305 accepted-value
  contract.
- [x] Public/grant jobs cannot use remote fallback unless a future signed grant
  policy explicitly allows it.

## Implementation Notes

- Added `reviewed_completion_answer_key` to the source-bound ingestion overlay
  contract, mutually exclusive with `manual_answer_key` and `review_decision`.
- Added shared candidate payload validation/digest helpers so Task 297
  advisory reports and Task 306 reviewed application use the same canonical
  payload semantics.
- Added effective-only answer-key provenance (`reviewed`,
  `teacher_provided`) and bounded lineage in `digiexam_effective_exam_v2`.
- Wired
  `local_llm_apply_missing_machine_marked_with_review` through the DigiExam
  bundle builder as overlay application only. The completion runtime returns no
  report artifact and performs no provider calls for apply mode.
- Kept DigiExam matching out of the runtime; matching application remains a
  future `ExamAuthoringIR v1` consumer concern for matching-capable sources.

## Validation Evidence

- `pdm run openapi-export-v2`
- Focused Task 306 proof (`26 passed`): ingestion overlay tests, DigiExam
  bundle no-provider/apply-mode tests, advisory completion tests, and OpenAPI
  contract tests.
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `pdm run coverage-gate` (`1257 passed, 5 skipped`, coverage `95.48%`)
- `git diff --check`

## Stop Conditions

- Stop if applying a completion would overwrite source-bound evidence.
- Stop if matching pairs or gap accepted values are not first-class IR data.
- Stop if provider errors, invalid JSON, or schema failures can become answer
  keys.
- Stop if apply mode needs to call the provider, query prior jobs, or trust
  prior job storage to validate a submitted candidate.
- Stop if reviewed application requires raw prompts/responses, raw `.dxe`,
  result PDF text, student data, owner metadata, or artifact paths in reports.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
