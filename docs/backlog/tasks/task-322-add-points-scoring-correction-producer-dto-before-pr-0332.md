---
id: task-322-add-points-scoring-correction-producer-dto-before-pr-0332
title: Add points/scoring correction producer DTO before PR-0332
type: task
status: ready
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - answer-key-completion
  - teacher-overlay
  - scoring
  - effective-ir
  - skriptoteket
  - pr-0332
---

Small producer-owned prerequisite immediately before Skriptoteket `PR-0332`.

## Objective

Add the Sir Convert producer DTO and route contract needed for source-bound
teacher correction of item points before Skriptoteket implements the full
teacher correction workflow in `PR-0332`.

Point correction is not a browser-local affordance and must not be routed
through `effective_item_patch`, `manual_answer_key`,
`reviewed_completion_answer_key`, or `review_decision`. It needs its own
producer-owned overlay field so Sir Convert can validate the correction, apply
it only to effective renderer input, recompute target readiness, and prove the
result in effective IR plus PDF/QTI artifacts.

## PR Scope

- Define the source-bound points/scoring correction DTO in the v2 ingestion
  overlay contract.
- Bind each point correction to the same invariant used by other teacher
  overlays: source file SHA-256, source IR schema version, source IR SHA-256,
  item id, sequence, item type, and source item fingerprint.
- Validate point corrections before rendering. Invalid, stale, mismatched,
  duplicated, non-numeric, negative, or target-incompatible values must fail
  before PDF/QTI generation.
- Apply accepted point corrections to effective renderer input without mutating
  source IR, parser provenance, answer-key provenance, or advisory completion
  metadata.
- Include applied point corrections in the effective IR/report surface so
  Skriptoteket can project returned state instead of trusting local UI edits.
- Recompute target readiness after point correction application.
- Publish the generated OpenAPI/consumer contract impact needed by
  Skriptoteket before `PR-0332` starts implementation.
- Add PDF and QTI artifact proof that corrected points are present where the
  targets represent points and that target-specific unsupported scoring
  features are reported without silently dropping the item or the correction.

## Out of Scope

- Skriptoteket UI controls for editing points.
- Teacher correction of stems, prompts, choices, matching keys, or
  gapped/open-cloze accepted values.
- Scoring-policy, rubric, marking-matrix, partial-credit, or free-text
  assessment semantics beyond the bounded item point value required by the
  existing renderer targets.
- Any fallback that lets local UI state unlock artifact downloads before the
  corrected Sir Convert bundle is returned.

## Deliverables

- [ ] Source-bound points/scoring correction DTO added to the v2 ingestion
  overlay contract.
- [ ] DTO validation fails before rendering for stale binding, duplicate
  binding, invalid values, and target-incompatible point changes.
- [ ] Effective IR/report output includes applied point corrections and their
  source binding.
- [ ] Target readiness is recomputed from the corrected effective renderer
  input.
- [ ] Generated OpenAPI and consumer-impact notes are refreshed for
  Skriptoteket.
- [ ] Focused tests prove point corrections reach effective IR and returned
  PDF/QTI artifacts without source IR mutation.

## Acceptance Criteria

- [ ] A valid source-bound point correction is accepted and appears in the
  returned effective IR/report.
- [ ] A stale or mismatched point correction fails before rendering and does
  not create downloadable artifacts.
- [ ] A point correction cannot be submitted through item-content patches,
  answer-key overlays, or review decisions.
- [ ] PDF and QTI outputs include the corrected point value wherever the target
  artifact represents item points.
- [ ] Unsupported target scoring semantics are explicit readiness/report
  failures, not silent artifact degradation.
- [ ] Source IR, parser provenance, answer-key provenance, advisory completion
  metadata, and internal diagnostics are not mutated or leaked into
  teacher-facing artifacts.

## Validation Plan

- Focused overlay DTO/schema tests.
- Focused effective IR/report projection tests.
- Focused PDF/QTI artifact inspection tests for corrected point values.
- OpenAPI generation no-drift proof.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
