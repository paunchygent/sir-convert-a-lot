---
id: task-298-define-matching-answer-key-pair-ir-contract
title: Define matching answer-key pair IR contract
type: task
status: proposed
priority: high
created: '2026-05-14'
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
  - matching
  - ir-contract
  - source-adapter
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and implement the matching answer-key pair contract in the Sir
Convert-owned intermediary/effective exam shape before any teacher overlay,
LLM advisory output, reviewed application, QTI export, or PDF renderer claims
matching can be machine-evaluated.

This task closes the parser-to-IR contract shape for matching items. It does
not implement LLM provider calls, advisory completion, reviewed application, or
model selection.

## PR Scope

- Add first-class matching answer-key pair fields to the source/effective IR
  contract, or create the smallest required schema version gate if an additive
  field is not safe.
- Preserve the existing observed matching structure: ordered left prompts,
  ordered right options, item IDs, source spans, and absent answer-key
  provenance when no trusted pairs exist.
- Add stable `left_id` and `right_id` bindings for matching prompts/options.
- Represent `correct_matching_pairs` as exact pairs of known IDs.
- Define right-option reuse policy explicitly, including whether many-left to
  one-right mappings are allowed by the source adapter.
- Validate that every referenced left/right ID exists and that required pairs
  are complete for the selected matching policy.
- Preserve source-bound parser provenance separately from teacher/manual or
  reviewed effective answer-key provenance.
- Update manifest, parity, manual-follow-up, target-readiness, PDF, and QTI
  contract docs where they depend on matching answer-key shape.
- Keep applied matching completion disabled until this contract and its
  validators are implemented.

## Deliverables

- [ ] Matching answer-key pair IR/effective-IR contract.
- [ ] Matching pair validation rules and failure/manual-follow-up semantics.
- [ ] Manifest/report shape for matching answer-key provenance.
- [ ] Renderer/QTI gate documentation proving matching remains manual/unkeyed
  unless trusted pairs exist.
- [ ] Focused tests for exact pair binding, missing IDs, duplicate/conflicting
  pairs, right-option reuse policy, source/effective provenance, and target
  readiness.

## Acceptance Criteria

- [ ] Matching answer-key pairs are first-class structured IR data, not prompt
  text, renderer labels, or provider-specific output.
- [ ] Source IR remains source-owned: missing pairs stay absent unless the
  source adapter or trusted evidence supplies them.
- [ ] Effective IR can carry teacher/manual or later reviewed matching pairs
  without rewriting parser provenance.
- [ ] Matching PDF/QTI output can distinguish source-proven, teacher/manual,
  reviewed effective, and absent answer-key provenance.
- [ ] Matching remains unavailable for automatic evaluation when exact pairs
  are missing, while Task 303 manual/unkeyed preservation remains available
  where schema/profile validation allows it.
- [ ] Reviewed application and LLM advisory tasks can consume the contract but
  are not implemented here.

## Stop Conditions

- Stop if matching pairs cannot be represented as exact ID-bound data.
- Stop if the implementation would infer correct pairs from visible prompt text
  without trusted source, teacher/manual, or reviewed evidence.
- Stop if QTI/PDF rendering would need target-specific labels inside the
  intermediary contract.
- Stop if many-left/right reuse semantics are ambiguous for the observed source
  evidence.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
