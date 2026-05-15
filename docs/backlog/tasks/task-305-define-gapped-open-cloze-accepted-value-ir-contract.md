---
id: task-305-define-gapped-open-cloze-accepted-value-ir-contract
title: Define gapped open-cloze accepted-value IR contract
type: task
status: proposed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
labels:
  - effective-ir
  - answer-key-completion
  - gap-fill
  - open-cloze
  - ir-contract
  - source-adapter
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and implement the accepted-value contract for gapped and open-cloze
items in the Sir Convert-owned intermediary/effective exam shape before any
teacher overlay, LLM advisory output, reviewed application, QTI export, or PDF
renderer claims such items can be machine-evaluated.

This task is the gapped/open-cloze sibling of Task 298. It closes the
parser-to-IR contract shape for gap identifiers and accepted values. It does
not implement LLM provider calls, advisory completion, reviewed application, or
model selection.

## PR Scope

- Define stable gap identifiers, visible gap order, prompt binding, and source
  spans for each gapped/open-cloze item.
- Represent accepted values per gap as first-class structured answer-key data.
- Define value normalization policy explicitly, including case, whitespace,
  punctuation, spelling variants, and whether normalization is target-specific
  or only used for validation.
- Define multi-gap completeness rules: which gaps must have trusted accepted
  values before the item can be automatically evaluated.
- Preserve source-bound parser provenance separately from teacher/manual or
  reviewed effective answer-key provenance.
- Preserve observed source gap IDs and avoid inventing values when no source,
  teacher/manual, or reviewed evidence exists.
- Update manifest, parity, manual-follow-up, target-readiness, PDF, and QTI
  contract docs where they depend on gap accepted-value shape.
- Keep applied gapped/open-cloze completion disabled until this contract and
  its validators are implemented.

## Deliverables

- [ ] Gapped/open-cloze accepted-value IR/effective-IR contract.
- [ ] Gap accepted-value validation rules and failure/manual-follow-up
  semantics.
- [ ] Manifest/report shape for gap answer-key provenance.
- [ ] Renderer/QTI gate documentation proving gap/open-cloze remains
  manual/unkeyed unless trusted accepted values exist.
- [ ] Focused tests for gap ID binding, missing gaps, duplicate/conflicting
  values, normalization, multi-gap completeness, source/effective provenance,
  and target readiness.

## Acceptance Criteria

- [ ] Gap accepted values are first-class structured IR data, not prompt text,
  renderer labels, or provider-specific output.
- [ ] Source IR remains source-owned: missing accepted values stay absent
  unless the source adapter or trusted evidence supplies them.
- [ ] Effective IR can carry teacher/manual or later reviewed accepted values
  without rewriting parser provenance.
- [ ] Gapped/open-cloze PDF/QTI output can distinguish source-proven,
  teacher/manual, reviewed effective, and absent answer-key provenance.
- [ ] Multi-gap items are unavailable for automatic evaluation until every
  required gap has trusted accepted values under the governed completeness
  policy.
- [ ] Task 303 manual/unkeyed preservation remains available where
  schema/profile validation allows it.
- [ ] Reviewed application and LLM advisory tasks can consume the contract but
  are not implemented here.

## Stop Conditions

- Stop if accepted values cannot be represented as exact gap-ID-bound data.
- Stop if the implementation would infer accepted values from visible prompt
  text without trusted source, teacher/manual, or reviewed evidence.
- Stop if QTI/PDF rendering would need target-specific labels inside the
  intermediary contract.
- Stop if normalization semantics would change source evidence or hide a
  teacher review decision.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
