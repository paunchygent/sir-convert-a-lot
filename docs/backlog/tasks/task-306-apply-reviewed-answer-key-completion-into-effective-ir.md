---
id: task-306-apply-reviewed-answer-key-completion-into-effective-ir
title: Apply reviewed answer-key completion into effective IR
type: task
status: proposed
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

## PR Scope

- Add effective answer-key provenance separate from source parser provenance.
- Apply validated completion only in
  `local_llm_apply_missing_machine_marked_with_review` mode.
- Require report/review semantics that distinguish LLM-inferred output from
  teacher/manual overlay.
- Preserve source-bound evidence precedence over LLM completion.
- Consume the choice, matching, and gapped/open-cloze structured answer-key
  contracts without widening their shape.
- Keep malformed or semantically invalid output as manual follow-up, with no
  repair.
- Prove teacher-accepted suggestions can be resubmitted as manual overlay, but
  are not retroactively model provenance.

## Deliverables

- [ ] Effective answer-key provenance model for reviewed completion.
- [ ] Apply mode for reviewed completion.
- [ ] Applied completion service.
- [ ] Completion report and effective IR update semantics.
- [ ] Renderer/QTI tests proving applied effective keys are consumed only after
  validation and review.

## Acceptance Criteria

- [ ] Source IR and parser provenance remain unchanged after applied
  completion.
- [ ] Effective IR and bundle manifest identify LLM-inferred answer keys
  explicitly.
- [ ] Teacher-accepted suggestions can be resubmitted as manual overlay, but
  are not retroactively model provenance.
- [ ] Matching application uses only the Task 298 exact pair contract.
- [ ] Gapped/open-cloze application uses only the Task 305 accepted-value
  contract.
- [ ] Public/grant jobs cannot use remote fallback unless a future signed grant
  policy explicitly allows it.

## Stop Conditions

- Stop if applying a completion would overwrite source-bound evidence.
- Stop if matching pairs or gap accepted values are not first-class IR data.
- Stop if provider errors, invalid JSON, or schema failures can become answer
  keys.
- Stop if reviewed application requires raw prompts/responses, raw `.dxe`,
  result PDF text, student data, owner metadata, or artifact paths in reports.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
