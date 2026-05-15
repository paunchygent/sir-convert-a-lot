---
id: task-298-implement-reviewed-answer-key-completion-application-and-matching-ir-v3-gate
title: Implement reviewed answer-key completion application and matching IR v3 gate
type: task
status: proposed
priority: high
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
labels:
  - effective-ir
  - answer-key-completion
  - matching
  - review-gate
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement reviewed application of validated answer-key completion into the
effective IR, including the IR v3 gate needed before matching answer pairs can
be applied.

## PR Scope

- Add effective answer-key provenance separate from source parser provenance.
- Apply validated completion only in
  `local_llm_apply_missing_machine_marked_with_review` mode.
- Require report/review semantics that distinguish LLM-inferred output from
  teacher/manual overlay.
- Preserve source-bound evidence precedence over LLM completion.
- Add matching answer-key pair fields before enabling applied matching
  completion.
- Keep malformed or semantically invalid output as manual follow-up, with no
  repair.

## Deliverables

- [ ] Effective answer-key provenance model.
- [ ] Effective IR schema update or explicit reuse decision.
- [ ] Applied completion service.
- [ ] Matching IR v3 answer-pair contract if matching is included.
- [ ] Renderer/QTI tests proving applied effective keys are consumed only after
  validation.

## Acceptance Criteria

- [ ] Source IR and parser provenance remain unchanged after applied
  completion.
- [ ] Effective IR and bundle manifest identify LLM-inferred answer keys
  explicitly.
- [ ] Teacher-accepted suggestions can be resubmitted as manual overlay, but
  are not retroactively model provenance.
- [ ] Matching answer application is blocked until exact left/right pairs exist
  in IR and validators prove all IDs are bound.
- [ ] Public/grant jobs cannot use remote fallback unless a future signed grant
  policy explicitly allows it.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
